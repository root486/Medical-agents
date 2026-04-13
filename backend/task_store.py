"""
任务状态持久化模块
使用SQLite数据库存储诊断任务状态
"""
import sqlite3
import json
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class TaskStore:
    """任务状态存储 - 基于SQLite"""
    
    def __init__(self, db_path: str = "task_store.db"):
        self.db_path = db_path
        self._init_database()
        logger.info(f"任务状态数据库初始化完成: {db_path}")
    
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self):
        """初始化数据库表"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # 创建任务状态表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_node TEXT NOT NULL,
                    state_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建时间线索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_user_id 
                ON tasks(user_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status 
                ON tasks(status)
            """)
            
            conn.commit()
            logger.info("数据库表初始化成功")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {str(e)}")
            raise
        finally:
            conn.close()
    
    def save_task(self, task_id: str, state: Dict[str, Any]):
        """
        保存或更新任务状态
        
        Args:
            task_id: 任务ID
            state: 任务状态字典
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # 序列化状态数据
            state_json = json.dumps(state, ensure_ascii=False, default=str)
            
            # 检查任务是否存在
            cursor.execute("SELECT task_id FROM tasks WHERE task_id = ?", (task_id,))
            exists = cursor.fetchone() is not None
            
            if exists:
                # 更新现有任务
                cursor.execute("""
                    UPDATE tasks 
                    SET status = ?, 
                        current_node = ?, 
                        state_data = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                """, (
                    state.get("status", "pending"),
                    state.get("current_node", "__start__"),
                    state_json,
                    task_id
                ))
            else:
                # 插入新任务
                cursor.execute("""
                    INSERT INTO tasks (task_id, user_id, status, current_node, state_data)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    task_id,
                    state.get("user_id", ""),
                    state.get("status", "pending"),
                    state.get("current_node", "__start__"),
                    state_json
                ))
            
            conn.commit()
            logger.debug(f"任务 {task_id} 状态已保存")
            
        except Exception as e:
            logger.error(f"保存任务状态失败: {str(e)}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态字典，不存在则返回None
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT state_data FROM tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            
            if row:
                state = json.loads(row["state_data"])
                logger.debug(f"任务 {task_id} 状态已加载")
                return state
            else:
                return None
                
        except Exception as e:
            logger.error(f"获取任务状态失败: {str(e)}")
            return None
        finally:
            conn.close()
    
    def delete_task(self, task_id: str):
        """
        删除任务
        
        Args:
            task_id: 任务ID
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            conn.commit()
            logger.info(f"任务 {task_id} 已删除")
        except Exception as e:
            logger.error(f"删除任务失败: {str(e)}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_user_tasks(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取用户的历史任务列表
        
        Args:
            user_id: 用户ID
            limit: 返回数量限制
            
        Returns:
            任务列表
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT task_id, status, current_node, created_at, updated_at
                FROM tasks 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))
            
            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    "task_id": row["task_id"],
                    "status": row["status"],
                    "current_node": row["current_node"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                })
            
            return tasks
            
        except Exception as e:
            logger.error(f"获取用户任务列表失败: {str(e)}")
            return []
        finally:
            conn.close()
    


# 全局任务存储实例
task_store_db = TaskStore()


