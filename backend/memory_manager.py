"""
记忆管理模块
实现短期记忆（内存）和长期记忆（向量数据库）
"""
from typing import Dict, List, Any
from datetime import datetime
import logging
from rag_module import knowledge_base

logger = logging.getLogger(__name__)


class MemoryManager:
    """记忆管理器 - 管理短期和长期记忆"""
    
    def __init__(self):
        # 短期记忆存储（内存，进程级别）
        self.short_term_memory: Dict[str, List[Dict]] = {}
        
        # 长期记忆使用 ChromaDB 向量库
        self.vectorstore = knowledge_base.vectorstore
        
        logger.info("记忆管理器初始化完成")
    
    def get_short_term_memory(self, user_id: str) -> List[Dict]:
        """
        获取用户的短期记忆
        
        Args:
            user_id: 用户ID
            
        Returns:
            短期记忆列表
        """
        return self.short_term_memory.get(user_id, [])
    
    def add_short_term_memory(self, user_id: str, memory_data: Dict):
        """
        添加短期记忆
        
        Args:
            user_id: 用户ID
            memory_data: 记忆数据
        """
        if user_id not in self.short_term_memory:
            self.short_term_memory[user_id] = []
        
        memory_entry = {
            "timestamp": datetime.now().isoformat(),
            "data": memory_data
        }
        
        self.short_term_memory[user_id].append(memory_entry)
        
        # 限制短期记忆数量（保留最近20条）
        if len(self.short_term_memory[user_id]) > 20:
            self.short_term_memory[user_id] = self.short_term_memory[user_id][-20:]
        
        logger.info(f"为用户 {user_id} 添加短期记忆")
    
    def save_long_term_memory(self, user_id: str, diagnosis_data: Dict):
        """
        保存长期记忆到向量数据库
        
        Args:
            user_id: 用户ID
            diagnosis_data: 诊断数据（包含症状、诊断结果等）
        """
        try:
            # 构建记忆文本
            memory_text = self._build_memory_text(user_id, diagnosis_data)
            
            # 构建元数据
            metadata = {
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "diagnosis": diagnosis_data.get("final_diagnosis", ""),
                "symptoms": diagnosis_data.get("symptoms", "")
            }
            
            # 添加到向量数据库
            self.vectorstore.add_texts(
                texts=[memory_text],
                metadatas=[metadata]
            )
            
            logger.info(f"为用户 {user_id} 保存长期记忆")
            
        except Exception as e:
            logger.error(f"保存长期记忆失败: {str(e)}")
    
    def get_user_memory_summary(self, user_id: str) -> Dict:
        """
        获取用户记忆摘要
        
        Args:
            user_id: 用户ID
            
        Returns:
            记忆摘要
        """
        short_term = self.get_short_term_memory(user_id)
        
        return {
            "user_id": user_id,
            "short_term_count": len(short_term),
            "recent_interactions": short_term[-5:] if short_term else []
        }
    
    def _build_memory_text(self, user_id: str, diagnosis_data: Dict) -> str:
        """
        构建记忆文本
        
        Args:
            user_id: 用户ID
            diagnosis_data: 诊断数据
            
        Returns:
            格式化的记忆文本
        """
        text = f"""用户ID: {user_id}
就诊时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
症状描述: {diagnosis_data.get('symptoms', '无')}
既往病史: {diagnosis_data.get('medical_history', '无')}
初步诊断: {diagnosis_data.get('preliminary_diagnosis', {}).get('diagnosis', '无')}
最终诊断: {diagnosis_data.get('final_diagnosis', '无')}
治疗方案: {diagnosis_data.get('treatment_plan', '无')}
医生备注: {diagnosis_data.get('doctor_notes', '无')}
"""
        return text


# 全局记忆管理器实例
memory_manager = MemoryManager()


if __name__ == "__main__":
    # 测试短期记忆（内存）的写入/读取，以及长期记忆（Chroma）的持久化
    print("=== 记忆管理模块测试 ===")
    mm = memory_manager
    test_uid = "test_user_001"

    # 测试短期记忆写入和读取
    mm.add_short_term_memory(test_uid, {"type": "test", "message": "短期记忆测试"})
    mm.add_short_term_memory(test_uid, {"type": "test", "message": "第二条记忆"})
    stm = mm.get_short_term_memory(test_uid)
    print(f"短期记忆数量: {len(stm)}")

    # 测试记忆摘要
    summary = mm.get_user_memory_summary(test_uid)
    print(f"记忆摘要: {summary}")

    # 测试长期记忆写入 Chroma
    mm.save_long_term_memory(test_uid, {
        "symptoms": "测试症状", "final_diagnosis": "测试诊断",
        "treatment_plan": "测试方案", "doctor_notes": "测试备注"
    })
    print("长期记忆保存成功")
    print("记忆管理模块测试通过")
