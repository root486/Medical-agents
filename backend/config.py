"""
医疗辅助诊断系统 - 配置管理
"""
from pydantic_settings import BaseSettings
import os

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Settings(BaseSettings):
    """应用配置类"""
    
    # 通义千问 API 配置
    DASHSCOPE_API_KEY: str = "sk-72d55594600d4425be44a478b6a9fb92"
    
    # MCP Server 配置（使用本地Python脚本）
    MCP_SERVER_ARGS: str = os.path.join(_BASE_DIR, "mcp_server.py")
    
    # Chroma 数据库配置
    CHROMA_PERSIST_DIR: str = os.path.join(_BASE_DIR, "chroma_db")
    
    # 知识库配置
    KNOWLEDGE_BASE_DIR: str = os.path.join(_BASE_DIR, "knowledge_base")
    
    # 应用配置
    APP_NAME: str = "医疗辅助诊断多智能体系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 全局配置实例
settings = Settings()



