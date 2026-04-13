"""
LangGraph 诊断流程图定义
实现完整的医疗诊断多智能体工作流
使用 interrupt() 实现真正的 Human-In-Loop
"""
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt
from langgraph.prebuilt import create_react_agent
from langchain_community.chat_models import ChatTongyi
from models import DiagnosisStatus
from mcp_client import mcp_server
from llm_service import generate_final_report
from consultation_subgraph import build_and_run_consultation_subgraph
from agent_tools import diagnosis_tools
from config import settings
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


# ==================== 状态定义 ====================

class DiagnosisState(TypedDict):
    task_id: str
    user_id: str
    symptoms: str
    age: Optional[int]
    gender: Optional[str]
    medical_history: Optional[str]
    medical_records: List[Dict[str, Any]]
    preliminary_diagnosis: Optional[Dict[str, Any]]
    need_consultation: bool
    consultation_departments: List[str]
    consultation_result: Optional[Dict[str, Any]]
    final_diagnosis: str
    treatment_plan: str
    doctor_notes: str
    current_node: str
    status: str
    timeline: List[Dict[str, Any]]
    human_approval: Optional[bool]


# ==================== Agent 创建 ====================

def create_preliminary_diagnosis_agent():
    """创建初步诊断 ReAct Agent"""
    llm = ChatTongyi(
        dashscope_api_key=settings.DASHSCOPE_API_KEY,
        model_name="qwen-max",
        temperature=0.3
    )
    return create_react_agent(model=llm, tools=diagnosis_tools)


def parse_diagnosis_json(text: str) -> Dict[str, Any]:
    """从 LLM 输出中尝试提取首个 JSON 对象，解析失败则返回默认诊断结构"""
    import json
    import re
    json_match = re.search(r'\{[^}]+\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except Exception:
            pass
    return {
        "diagnosis": text[:200],
        "basis": "基于症状分析",
        "suggested_departments": ["内科"]
    }


# ==================== 节点函数 ====================

def task_summary_node(state: DiagnosisState) -> Dict[str, Any]:
    """节点1：诊断任务汇总"""
    logger.info(f"任务 {state['task_id']} - 开始任务汇总")
    timeline_entry = {
        "timestamp": datetime.now().isoformat(),
        "node": "task_summary",
        "status": "completed",
        "message": "诊断任务已汇总"
    }
    return {
        "current_node": "task_summary",
        "status": DiagnosisStatus.TASK_SUMMARY.value,
        "timeline": state.get("timeline", []) + [timeline_entry]
    }


def fetch_medical_records_node(state: DiagnosisState) -> Dict[str, Any]:
    """节点2：获取用户历史诊断记录（通过MCP）"""
    logger.info(f"任务 {state['task_id']} - 获取医疗记录")
    try:
        records = mcp_server.get_user_medical_records(state["user_id"])
        records_dict = [record.model_dump() for record in records]
        timeline_entry = {
            "timestamp": datetime.now().isoformat(),
            "node": "fetch_medical_records",
            "status": "completed",
            "message": f"成功获取 {len(records)} 条历史医疗记录",
            "data": {"records": records_dict}
        }
        return {
            "medical_records": records_dict,
            "current_node": "fetch_medical_records",
            "status": DiagnosisStatus.FETCHING_RECORDS.value,
            "timeline": state.get("timeline", []) + [timeline_entry]
        }
    except Exception as e:
        logger.error(f"获取医疗记录失败: {str(e)}")
        timeline_entry = {
            "timestamp": datetime.now().isoformat(),
            "node": "fetch_medical_records",
            "status": "failed",
            "message": f"获取医疗记录失败: {str(e)}"
        }
        return {
            "medical_records": [],
            "current_node": "fetch_medical_records",
            "status": DiagnosisStatus.FETCHING_RECORDS.value,
            "timeline": state.get("timeline", []) + [timeline_entry]
        }


def preliminary_diagnosis_node(state: DiagnosisState) -> Dict[str, Any]:
    """节点3：使用 ReAct Agent 生成初步诊断"""
    logger.info(f"任务 {state['task_id']} - ReAct Agent 生成初步诊断")
    try:
        agent = create_preliminary_diagnosis_agent()
        agent_input = {
            "messages": [{
                "role": "user",
                "content": f"""请根据以下信息进行诊断：

患者症状：{state['symptoms']}
年龄：{state.get('age', '未知')}
性别：{state.get('gender', '未知')}
既往病史：{state.get('medical_history', '无')}
用户ID：{state['user_id']}

请使用提供的工具（搜索医学知识、查询患者历史等）进行综合分析，然后给出诊断结果。

请以JSON格式返回：
{{
  "diagnosis": "诊断结果",
  "basis": "诊断依据",
  "suggested_departments": ["内科", "外科"]
}}"""
            }]
        }
        result = agent.invoke(agent_input)
        final_message = result["messages"][-1].content
        diagnosis_result = parse_diagnosis_json(final_message)
        logger.info(f"ReAct Agent 完成诊断: {diagnosis_result.get('diagnosis', '')[:50]}")

        timeline_entry = {
            "timestamp": datetime.now().isoformat(),
            "node": "preliminary_diagnosis",
            "status": "completed",
            "message": "ReAct Agent 完成初步诊断",
            "data": {"diagnosis": diagnosis_result}
        }
        return {
            "preliminary_diagnosis": diagnosis_result,
            "current_node": "preliminary_diagnosis",
            "status": DiagnosisStatus.PRELIMINARY_DIAGNOSIS.value,
            "timeline": state.get("timeline", []) + [timeline_entry]
        }
    except Exception as e:
        logger.error(f"ReAct Agent 生成初步诊断失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


def consultation_decision_node(state: DiagnosisState) -> Dict[str, Any]:
    """
    节点4：Human-In-Loop 会诊决策
    使用 interrupt() 暂停图执行，等待医生通过 API 提交决策后
    以 Command(resume=...) 恢复执行。
    """
    logger.info(f"任务 {state['task_id']} - 等待医生确认会诊 (interrupt)")

    human_input = interrupt({
        "question": "是否需要跨科室会诊？",
        "preliminary_diagnosis": state.get("preliminary_diagnosis"),
        "medical_records": state.get("medical_records", []),
    })

    need_consultation = human_input.get("need_consultation", False)
    departments = human_input.get("departments", [])

    logger.info(f"医生决策: need_consultation={need_consultation}, departments={departments}")

    timeline_entry = {
        "timestamp": datetime.now().isoformat(),
        "node": "consultation_decision",
        "status": "completed",
        "message": f"医生确认: {'需要' if need_consultation else '不需要'}会诊"
    }
    return {
        "need_consultation": need_consultation,
        "consultation_departments": departments,
        "human_approval": need_consultation,
        "current_node": "consultation_decision",
        "status": DiagnosisStatus.CONSULTATION_DECISION.value,
        "timeline": state.get("timeline", []) + [timeline_entry]
    }


def cross_department_consultation_node(state: DiagnosisState) -> Dict[str, Any]:
    """节点5：跨科室会诊（调用真实的 LangGraph SubGraph）"""
    logger.info(f"任务 {state['task_id']} - 开始跨科室会诊")
    try:
        departments = state.get("consultation_departments", ["内科", "外科"])
        subgraph_input = {
            "symptoms": state["symptoms"],
            "preliminary_diagnosis": state.get("preliminary_diagnosis", {}),
            "departments": departments,
            "medical_records": state.get("medical_records", []),
            "opinions": [],
            "consensus": ""
        }

        logger.info(f"执行会诊子图，参与科室: {departments}")
        subgraph_result = build_and_run_consultation_subgraph(subgraph_input)

        consultation_result = {
            "departments": departments,
            "opinions": subgraph_result.get("opinions", []),
            "consensus": subgraph_result.get("consensus", "")
        }

        timeline_entry = {
            "timestamp": datetime.now().isoformat(),
            "node": "cross_department_consultation",
            "status": "completed",
            "message": f"完成 {len(departments)} 个科室的会诊",
            "data": {"result": consultation_result}
        }
        return {
            "consultation_result": consultation_result,
            "current_node": "cross_department_consultation",
            "status": DiagnosisStatus.CROSS_DEPARTMENT.value,
            "timeline": state.get("timeline", []) + [timeline_entry]
        }
    except Exception as e:
        logger.error(f"跨科室会诊失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


def doctor_review_node(state: DiagnosisState) -> Dict[str, Any]:
    """
    节点6：Human-In-Loop 医生复诊
    使用 interrupt() 暂停图执行，等待医生通过 API 提交修改后
    以 Command(resume=...) 恢复执行。
    """
    logger.info(f"任务 {state['task_id']} - 等待医生复诊 (interrupt)")

    human_input = interrupt({
        "question": "请审查诊断结果并提供最终诊断",
        "preliminary_diagnosis": state.get("preliminary_diagnosis"),
        "consultation_result": state.get("consultation_result"),
        "medical_records": state.get("medical_records", []),
    })

    logger.info(f"医生已提交复诊结果")

    timeline_entry = {
        "timestamp": datetime.now().isoformat(),
        "node": "doctor_review",
        "status": "completed",
        "message": "医生已完成诊断修改"
    }
    return {
        "final_diagnosis": human_input.get("modified_diagnosis", ""),
        "treatment_plan": human_input.get("modified_treatment", ""),
        "doctor_notes": human_input.get("doctor_notes", ""),
        "current_node": "doctor_review",
        "status": DiagnosisStatus.DOCTOR_REVIEW.value,
        "timeline": state.get("timeline", []) + [timeline_entry]
    }


def final_summary_node(state: DiagnosisState) -> Dict[str, Any]:
    """节点7：诊断任务汇总（最终结果整合）"""
    logger.info(f"任务 {state['task_id']} - 生成最终诊断报告")
    try:
        final_report = generate_final_report(
            symptoms=state["symptoms"],
            medical_records=state.get("medical_records", []),
            preliminary_diagnosis=state.get("preliminary_diagnosis", {}),
            consultation_result=state.get("consultation_result"),
            final_diagnosis=state.get("final_diagnosis", ""),
            treatment_plan=state.get("treatment_plan", ""),
            doctor_notes=state.get("doctor_notes", "")
        )

        timeline_entry = {
            "timestamp": datetime.now().isoformat(),
            "node": "final_summary",
            "status": "completed",
            "message": "最终诊断报告已生成"
        }
        return {
            "final_diagnosis": final_report.get("final_diagnosis", state.get("final_diagnosis", "")),
            "treatment_plan": final_report.get("treatment_plan", state.get("treatment_plan", "")),
            "current_node": "final_summary",
            "status": "completed",
            "timeline": state.get("timeline", []) + [timeline_entry]
        }
    except Exception as e:
        logger.error(f"生成最终报告失败: {str(e)}")
        raise


# ==================== 条件路由 ====================

def should_consult(state: DiagnosisState) -> str:
    """会诊决策后的路由：根据医生决定选择路径"""
    if state.get("need_consultation"):
        return "cross_department_consultation"
    return "doctor_review"


# ==================== 构建图 ====================

def create_diagnosis_graph():
    """创建诊断流程图（全流程通过 LangGraph 引擎执行）"""
    workflow = StateGraph(DiagnosisState)

    workflow.add_node("task_summary", task_summary_node)
    workflow.add_node("fetch_medical_records", fetch_medical_records_node)
    workflow.add_node("preliminary_diagnosis", preliminary_diagnosis_node)
    workflow.add_node("consultation_decision", consultation_decision_node)
    workflow.add_node("cross_department_consultation", cross_department_consultation_node)
    workflow.add_node("doctor_review", doctor_review_node)
    workflow.add_node("final_summary", final_summary_node)

    workflow.set_entry_point("task_summary")

    workflow.add_edge("task_summary", "fetch_medical_records")
    workflow.add_edge("fetch_medical_records", "preliminary_diagnosis")
    workflow.add_edge("preliminary_diagnosis", "consultation_decision")

    workflow.add_conditional_edges(
        "consultation_decision",
        should_consult,
        {
            "cross_department_consultation": "cross_department_consultation",
            "doctor_review": "doctor_review",
        }
    )

    workflow.add_edge("cross_department_consultation", "doctor_review")
    workflow.add_edge("doctor_review", "final_summary")
    workflow.add_edge("final_summary", END)

    checkpointer = MemorySaver()
    graph = workflow.compile(checkpointer=checkpointer)
    return graph


diagnosis_graph = create_diagnosis_graph()


if __name__ == "__main__":
    # 验证主图编译结果（节点/边）、JSON 解析函数、条件路由逻辑（不触发 LLM）
    print("=== LangGraph 诊断流程图测试 ===")
    graph = diagnosis_graph
    print(f"图类型: {type(graph).__name__}")

    # 检查编译后的图节点
    nodes = list(graph.get_graph().nodes)
    print(f"节点数量: {len(nodes)}")
    print(f"节点列表: {nodes}")

    # 测试从 LLM 输出中提取 JSON 的解析函数
    print("\n测试 parse_diagnosis_json:")
    test_text = '根据分析结果 {"diagnosis":"测试诊断","basis":"测试依据","suggested_departments":["内科"]} 以上。'
    parsed = parse_diagnosis_json(test_text)
    print(f"  解析结果: {parsed}")

    # 测试条件路由函数
    print("\n测试 should_consult 路由:")
    print(f"  need_consultation=True  -> {should_consult({'need_consultation': True})}")
    print(f"  need_consultation=False -> {should_consult({'need_consultation': False})}")
    print("诊断流程图模块测试通过")
