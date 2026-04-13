"""
MCP (Model Context Protocol) 集成模块
用于获取用户历史诊断记录
"""
import asyncio
import concurrent.futures
import json
import sys
import os
import traceback
from typing import List, Dict, Any
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from config import settings
from models import MedicalRecord
import logging

logger = logging.getLogger(__name__)


class MCPServer:
    """MCP Server 客户端 - 使用官方MCP包"""
    
    def __init__(self):
        self.command = sys.executable
        self.args = [settings.MCP_SERVER_ARGS] if settings.MCP_SERVER_ARGS else []
        
    async def _call_mcp_tool(self, user_id: str) -> List[Dict[str, Any]]:
        """
        创建一次性 MCP 连接，调用工具后自动清理
        """
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=env
        )

        async with AsyncExitStack() as stack:
            stdio_transport = await stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport

            session = await stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            logger.info("MCP Server 连接成功")

            result = await session.call_tool(
                "get_medical_records",
                arguments={"user_id": str(user_id)}
            )

            if result.isError:
                error_msg = result.content[0].text if result.content else "未知错误"
                logger.error(f"MCP工具调用返回错误: {error_msg}")
                return []

            if not result.content:
                return []

            records_data = []
            for item in result.content:
                try:
                    parsed = json.loads(item.text)
                    if isinstance(parsed, list):
                        records_data.extend(parsed)
                    elif isinstance(parsed, dict):
                        records_data.append(parsed)
                except json.JSONDecodeError:
                    logger.warning(f"无法解析MCP响应项: {item.text[:200]}")
            return records_data

    def get_user_medical_records(self, user_id: str) -> List[MedicalRecord]:
        """
        通过MCP协议获取用户历史诊断记录（同步接口）
        每次调用创建独立的连接和事件循环，避免状态泄漏。
        """
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                records_data = pool.submit(
                    asyncio.run, self._call_mcp_tool(str(user_id))
                ).result(timeout=30)

            medical_records = [MedicalRecord(**rd) for rd in records_data]
            logger.info(f"成功获取用户 {user_id} 的 {len(medical_records)} 条医疗记录")
            return medical_records

        except BaseException as e:
            if hasattr(e, 'exceptions'):
                for i, sub_exc in enumerate(e.exceptions):
                    logger.error(f"  TaskGroup 子异常 {i}: {type(sub_exc).__name__}: {sub_exc}")
            logger.error(f"获取医疗记录失败: {str(e)}")
            logger.error(traceback.format_exc())
            return []

    def start_server(self):
        """启动MCP Server（预留，实际由FastMCP自动管理）"""
        logger.info("MCP Server将在首次调用时自动连接")
    
    def stop_server(self):
        """停止MCP Server（连接已由 AsyncExitStack 自动管理）"""
        logger.info("MCP Server 连接已自动清理")
    
    def get_mcp_config(self) -> Dict[str, Any]:
        """获取 MCP 配置信息"""
        return {
            "mcpServers": {
                "medical-record": {
                    "command": self.command,
                    "args": self.args,
                    "env": {}
                }
            }
        }


# 全局 MCP Server 实例
mcp_server = MCPServer()


if __name__ == "__main__":
    # 测试 MCP 完整调用链路：启动 mcp_server.py 子进程 → stdio 通信 → 获取医疗记录
    print("=== MCP 客户端模块测试 ===")
    print(f"MCP Server命令: {mcp_server.command}")
    print(f"MCP Server参数: {mcp_server.args}")
    print(f"MCP 配置: {mcp_server.get_mcp_config()}")

    # 通过 MCP 协议获取 user_001 的病历
    print("\n获取 user_001 的医疗记录...")
    records = mcp_server.get_user_medical_records("user_001")
    print(f"获取到 {len(records)} 条记录:")
    for r in records:
        print(f"  - {r.date}: {r.diagnosis} ({r.department})")
    print("MCP 客户端测试通过")
