"""
跨科室会诊子图模块
使用真实的 LangGraph SubGraph 实现多智能体协作会诊
"""
from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from langchain_community.chat_models import ChatTongyi
from agent_tools import diagnosis_tools
from config import settings
import logging

logger = logging.getLogger(__name__)


def merge_opinions(left: List[Dict], right: List[Dict]) -> List[Dict]:
    """合并各科室意见（Annotated reducer）"""
    return left + right


class ConsultationState(TypedDict):
    """会诊子图状态"""
    symptoms: str
    preliminary_diagnosis: Dict[str, Any]
    departments: List[str]
    medical_records: List[Dict[str, Any]]
    opinions: Annotated[List[Dict[str, str]], merge_opinions]
    consensus: str


def create_department_agent(department: str):
    """为指定科室创建 ReAct Agent 节点函数"""
    def department_agent_node(state: ConsultationState) -> Dict[str, Any]:
        logger.info(f"会诊子图 - {department} ReAct Agent 正在分析")
        try:
            llm = ChatTongyi(
                dashscope_api_key=settings.DASHSCOPE_API_KEY,
                model_name="qwen-max",
                temperature=0.3
            )
            agent = create_react_agent(model=llm, tools=diagnosis_tools)

            agent_input = {
                "messages": [{
                    "role": "user",
                    "content": f"""请从{department}的专业角度对以下病例进行会诊：

【患者症状】
{state['symptoms']}

【初步诊断】
{state['preliminary_diagnosis'].get('diagnosis', '待诊断')}

【诊断依据】
{state['preliminary_diagnosis'].get('basis', '无')}

请使用工具搜索相关医学知识，然后给出会诊意见（150字以内）：
- 对该诊断的看法
- 需要补充的检查
- 治疗建议"""
                }]
            }

            result = agent.invoke(agent_input)
            opinion = result["messages"][-1].content
            logger.info(f"{department} ReAct Agent 完成意见生成")

            return {
                "opinions": [{"department": department, "opinion": opinion.strip()}]
            }
        except Exception as e:
            logger.error(f"{department} ReAct Agent 执行失败: {str(e)}")
            return {
                "opinions": [{"department": department, "opinion": f"{department}因技术原因未能提供意见"}]
            }

    return department_agent_node


def generate_consensus_node(state: ConsultationState) -> Dict[str, Any]:
    """生成会诊共识节点"""
    logger.info("会诊子图 - 生成会诊共识")
    try:
        llm = ChatTongyi(
            dashscope_api_key=settings.DASHSCOPE_API_KEY,
            model_name="qwen-max",
            temperature=0.2
        )

        opinions_text = "\n\n".join([
            f"【{op['department']}】\n{op['opinion']}"
            for op in state.get('opinions', [])
        ])

        prompt = f"""作为会诊主持人，请根据以下各科室专家意见，生成会诊共识（200字以内）：

{opinions_text}

会诊共识："""

        consensus = llm.invoke(prompt)
        logger.info("会诊共识生成完成")
        return {"consensus": consensus.content.strip()}
    except Exception as e:
        logger.error(f"生成会诊共识失败: {str(e)}")
        return {"consensus": "因技术原因未能生成会诊共识"}


def build_and_run_consultation_subgraph(input_state: dict) -> dict:
    """
    根据科室列表动态构建 LangGraph SubGraph 并执行。
    每个科室是图中的一个真实节点，最后汇入共识节点。
    """
    departments = input_state.get("departments", ["内科", "外科"])
    logger.info(f"构建会诊子图，参与科室: {departments}")

    subgraph = StateGraph(ConsultationState)

    prev_node = None
    for dept in departments:
        node_name = f"dept_{dept}"
        subgraph.add_node(node_name, create_department_agent(dept))
        if prev_node is None:
            subgraph.set_entry_point(node_name)
        else:
            subgraph.add_edge(prev_node, node_name)
        prev_node = node_name

    subgraph.add_node("generate_consensus", generate_consensus_node)
    subgraph.add_edge(prev_node, "generate_consensus")
    subgraph.add_edge("generate_consensus", END)

    compiled = subgraph.compile()
    logger.info("会诊子图编译完成，开始执行")

    result = compiled.invoke(input_state)

    logger.info(f"会诊子图执行完成，共{len(result.get('opinions', []))}个科室参与")
    return result


if __name__ == "__main__":
    # 验证子图能否根据科室列表动态构建并编译（不实际执行，避免 LLM 调用）
    print("=== 跨科室会诊子图测试 ===")
    departments = ["内科", "外科", "神经内科"]
    print(f"测试科室: {departments}")

    # 动态构建子图：每个科室一个 Agent 节点 + 共识汇总节点
    subgraph = StateGraph(ConsultationState)
    prev = None
    for dept in departments:
        node_name = f"dept_{dept}"
        subgraph.add_node(node_name, create_department_agent(dept))
        if prev is None:
            subgraph.set_entry_point(node_name)
        else:
            subgraph.add_edge(prev, node_name)
        prev = node_name
    subgraph.add_node("generate_consensus", generate_consensus_node)
    subgraph.add_edge(prev, "generate_consensus")
    subgraph.add_edge("generate_consensus", END)
    compiled = subgraph.compile()

    # 检查编译后的子图节点
    nodes = list(compiled.get_graph().nodes)
    print(f"子图节点数量: {len(nodes)}")
    print(f"子图节点列表: {nodes}")
    print("子图构建验证通过（跳过实际执行以避免 LLM 调用）")
