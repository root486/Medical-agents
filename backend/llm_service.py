"""
大语言模型服务模块
使用通义千问API生成最终诊断报告
"""
from typing import List, Dict, Any, Optional
from langchain_community.llms import Tongyi
from config import settings
import logging

logger = logging.getLogger(__name__)


def generate_final_report(
    symptoms: str,
    medical_records: List[Dict[str, Any]],
    preliminary_diagnosis: Dict[str, Any],
    consultation_result: Optional[Dict[str, Any]],
    final_diagnosis: str,
    treatment_plan: str,
    doctor_notes: str
) -> Dict[str, Any]:
    """
    生成最终诊断报告
    
    Args:
        symptoms: 症状
        medical_records: 医疗记录
        preliminary_diagnosis: 初步诊断
        consultation_result: 会诊结果
        final_diagnosis: 最终诊断
        treatment_plan: 治疗方案
        doctor_notes: 医生备注
        
    Returns:
        包含 final_diagnosis、treatment_plan 的字典
    """
    try:
        llm = Tongyi(
            dashscope_api_key=settings.DASHSCOPE_API_KEY,
            model_name="qwen-max",
            temperature=0.2
        )
        
        # 如果没有提供最终诊断，使用初步诊断
        if not final_diagnosis:
            final_diagnosis = preliminary_diagnosis.get("diagnosis", "待诊断")
        
        # 如果没有提供治疗方案，生成一个
        if not treatment_plan:
            prompt = f"""根据以下诊断，制定详细的治疗方案：

诊断：{final_diagnosis}
症状：{symptoms}

请提供：
1. 药物治疗
2. 生活方式建议
3. 复查时间
4. 注意事项"""
            
            treatment_plan = llm.invoke(prompt)
        
        result = {
            "final_diagnosis": final_diagnosis,
            "treatment_plan": treatment_plan,
        }
        
        logger.info("生成最终诊断报告完成")
        return result
        
    except Exception as e:
        logger.error(f"生成最终报告失败: {str(e)}")
        raise



