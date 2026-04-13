"""
医疗辅助诊断多智能体系统 - FastAPI 主应用
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import uvicorn

from config import settings
from api_routes import router as api_router
from rag_module import knowledge_base
from database import engine
from db_models import Base
from mcp_client import mcp_server

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="基于LangGraph的医疗辅助诊断多智能体Agent系统"
)

# 配置CORS（跨域支持）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router)


@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    # 创建所有数据库表
    Base.metadata.create_all(bind=engine)
    
    logger.info("=" * 50)
    logger.info("医疗辅助诊断多智能体系统启动中...")
    logger.info("=" * 50)
    
    try:
        # 启动MCP Server
        logger.info("正在启动MCP Server...")
        mcp_server.start_server()
        logger.info("✓ MCP Server启动完成")
    except Exception as e:
        logger.error(f"✗ MCP Server启动失败: {str(e)}")
    
    try:
        # 加载医疗知识库
        logger.info("正在加载医疗知识库...")
        knowledge_base.load_knowledge_base()
        logger.info("✓ 医疗知识库加载完成")
    except Exception as e:
        logger.error(f"✗ 知识库加载失败: {str(e)}")
    
    logger.info("=" * 50)
    logger.info("系统启动完成！")
    logger.info(f"API文档地址: http://localhost:8000/docs")
    logger.info("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info("正在关闭MCP Server...")
    mcp_server.stop_server()
    logger.info("系统已关闭")


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    # 运行服务器
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
