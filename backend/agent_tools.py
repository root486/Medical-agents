"""
ReAct Agent 工具集
为医疗诊断Agent提供可调用的工具
"""
from langchain_core.tools import tool
from rag_module import knowledge_base
from mcp_client import mcp_server
import logging

logger = logging.getLogger(__name__)


@tool
def search_medical_knowledge(query: str) -> str:
    """
    搜索医学知识库，获取相关疾病诊疗信息
    
    Args:
        query: 搜索关键词，如症状、疾病名称等
        
    Returns:
        相关的医学知识文本
    """
    try:
        results = knowledge_base.search_knowledge(query, k=3)
        if not results:
            return "未找到相关医学知识"
        
        knowledge_text = "\n\n".join([r["content"] for r in results])
        return f"【检索到的医学知识】\n{knowledge_text}"
        
    except Exception as e:
        logger.error(f"医学知识搜索失败: {str(e)}")
        return f"搜索失败: {str(e)}"


@tool
def get_patient_history(user_id: str) -> str:
    """
    获取患者历史就诊记录
    
    Args:
        user_id: 患者ID
        
    Returns:
        历史就诊记录文本
    """
    try:
        records = mcp_server.get_user_medical_records(str(user_id))
        if not records:
            return "该患者无历史就诊记录"
        
        history_text = "\n\n".join([
            f"日期: {r.date}\n诊断: {r.diagnosis}\n治疗: {r.treatment}"
            for r in records[:5]  # 最多返回5条
        ])
        
        return f"【患者历史就诊记录】\n{history_text}"
        
    except Exception as e:
        logger.error(f"获取患者历史失败: {str(e)}")
        return f"获取失败: {str(e)}"


@tool
def calculate_bmi(weight: float, height: float) -> str:
    """
    计算BMI指数
    
    Args:
        weight: 体重（kg）
        height: 身高（cm）
        
    Returns:
        BMI值和评估结果
    """
    try:
        height_m = height / 100
        bmi = weight / (height_m ** 2)
        
        if bmi < 18.5:
            assessment = "偏瘦"
        elif bmi < 24:
            assessment = "正常"
        elif bmi < 28:
            assessment = "超重"
        else:
            assessment = "肥胖"
        
        return f"BMI: {bmi:.1f} ({assessment})"
        
    except Exception as e:
        return f"计算失败: {str(e)}"


# 工具列表
diagnosis_tools = [
    search_medical_knowledge,
    get_patient_history,
    calculate_bmi
]


if __name__ == "__main__":
    # 测试各 @tool 工具是否可正常调用（BMI 纯计算，知识库检索需 Chroma 就绪）
    print("=== ReAct Agent 工具集测试 ===")
    print(f"已注册工具数量: {len(diagnosis_tools)}")
    for t in diagnosis_tools:
        print(f"  - {t.name}: {t.description[:50]}...")

    # 测试 BMI 计算工具
    bmi_result = calculate_bmi.invoke({"weight": 70.0, "height": 175.0})
    print(f"\nBMI计算测试: 70kg/175cm -> {bmi_result}")

    # 测试知识库检索工具
    search_result = search_medical_knowledge.invoke({"query": "高血压"})
    print(f"知识库检索测试: {search_result[:80]}...")
    print("工具集测试通过")
