"""
Chroma 向量数据库和 RAG 检索模块
用于医疗知识库的存储和检索
"""
import os
from typing import List, Dict, Any
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import settings
import logging

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """医疗知识库管理类"""
    
    def __init__(self):
        self.persist_dir = settings.CHROMA_PERSIST_DIR
        self.knowledge_dir = settings.KNOWLEDGE_BASE_DIR
        self.collection_name = "medical_knowledge"
        
        # 初始化 embeddings（使用通义千问的embedding模型）
        self.embeddings = DashScopeEmbeddings(
            dashscope_api_key=settings.DASHSCOPE_API_KEY,
            model="text-embedding-v2"
        )
        
        # 确保目录存在
        os.makedirs(self.knowledge_dir, exist_ok=True)
        os.makedirs(self.persist_dir, exist_ok=True)
        
        try:
            import chromadb

            client = chromadb.PersistentClient(path=self.persist_dir)

            self.vectorstore = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                client=client
            )
            logger.info("ChromaDB 向量数据库初始化成功")
            
        except Exception as e:
            logger.error(f"ChromaDB初始化失败: {str(e)}")
            raise
        
        # 文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=len,
        )
    
    def load_knowledge_base(self):
        """加载本地TXT格式的医疗知识库"""
        try:
            # 读取所有TXT文件
            txt_files = [f for f in os.listdir(self.knowledge_dir) if f.endswith('.txt')]
            
            if not txt_files:
                logger.warning(f"知识库目录 {self.knowledge_dir} 中没有找到TXT文件")
                self._create_sample_knowledge()
                txt_files = [f for f in os.listdir(self.knowledge_dir) if f.endswith('.txt')]
            
            all_documents = []
            
            for txt_file in txt_files:
                file_path = os.path.join(self.knowledge_dir, txt_file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 分割文本
                texts = self.text_splitter.split_text(content)
                
                # 创建文档对象
                for i, text in enumerate(texts):
                    all_documents.append({
                        "content": text,
                        "source": txt_file,
                        "chunk_id": i
                    })
            
            # 添加到向量数据库
            if all_documents:
                texts = [doc["content"] for doc in all_documents]
                metadatas = [{"source": doc["source"], "chunk_id": doc["chunk_id"]} 
                            for doc in all_documents]
                
                self.vectorstore.add_texts(texts=texts, metadatas=metadatas)
                logger.info(f"成功加载 {len(all_documents)} 个知识片段到向量数据库")
            
        except Exception as e:
            logger.error(f"加载知识库失败: {str(e)}")
            raise
    
    def _create_sample_knowledge(self):
        """创建示例医疗知识库"""
        sample_knowledge = """
# 常见疾病诊疗指南

## 上呼吸道感染
症状：发热、咳嗽、流涕、咽痛
诊断要点：根据临床表现，血常规检查
治疗方案：
- 对症治疗：退热、止咳
- 抗病毒治疗：如为病毒感染
- 抗生素：如合并细菌感染
- 休息、多饮水

## 急性胃炎
症状：上腹痛、恶心、呕吐
诊断要点：病史、体格检查、胃镜
治疗方案：
- 禁食12-24小时
- 静脉补液
- 质子泵抑制剂（奥美拉唑等）
- 胃黏膜保护剂

## 高血压
症状：头晕、头痛、耳鸣
诊断要点：血压测量≥140/90mmHg
治疗方案：
- 生活方式干预：低盐饮食、运动
- 药物治疗：ACEI、ARB、CCB等
- 定期监测血压

## 糖尿病
症状：多饮、多食、多尿、体重下降
诊断要点：空腹血糖≥7.0mmol/L
治疗方案：
- 饮食控制
- 运动疗法
- 口服降糖药或胰岛素
- 血糖监测

## 冠心病
症状：胸痛、胸闷、心悸
诊断要点：心电图、冠脉CTA或造影
治疗方案：
- 抗血小板治疗
- 调脂治疗
- 血运重建（支架或搭桥）
- 生活方式干预
"""
        
        sample_file = os.path.join(self.knowledge_dir, "common_diseases.txt")
        with open(sample_file, 'w', encoding='utf-8') as f:
            f.write(sample_knowledge)
        
        logger.info(f"已创建示例知识库文件: {sample_file}")

    def search_knowledge(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        检索相关医疗知识
        
        Args:
            query: 查询文本
            k: 返回结果数量
            
        Returns:
            相关知识列表
        """
        try:
            # 相似度搜索
            results = self.vectorstore.similarity_search_with_score(query, k=k)
            
            knowledge_list = []
            for doc, score in results:
                knowledge_list.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": score
                })
            
            logger.info(f"检索到 {len(knowledge_list)} 条相关知识")
            return knowledge_list
            
        except Exception as e:
            logger.error(f"知识检索失败: {str(e)}")
            return []
    


# 全局知识库实例
knowledge_base = KnowledgeBase()


if __name__ == "__main__":
    # 测试完整 RAG 流程：加载 TXT → 切片 → Embedding → 存入 Chroma → 相似度检索
    print("=== RAG 知识库模块测试 ===")
    print(f"知识库目录: {knowledge_base.knowledge_dir}")
    print(f"向量库目录: {knowledge_base.persist_dir}")

    # 加载知识库到向量数据库
    knowledge_base.load_knowledge_base()
    print("知识库加载成功")

    # 测试语义检索
    results = knowledge_base.search_knowledge("发热咳嗽", k=2)
    print(f"检索 '发热咳嗽' 返回 {len(results)} 条结果:")
    for r in results:
        print(f"  - score={r['score']:.4f}: {r['content'][:60]}...")
    print("RAG 模块测试通过")
