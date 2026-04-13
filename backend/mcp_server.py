"""
MCP Server - 医疗记录服务
使用官方MCP包实现Model Context Protocol协议
"""
import logging
from typing import List, Dict, Any, Union
from mcp.server.fastmcp import FastMCP

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_server")

# 创建MCP Server实例
mcp = FastMCP("medical-record-server")


class MedicalRecordDatabase:
    """医疗记录数据库（示例数据，实际应连接真实数据库）"""
    
    def __init__(self):
        self.records_db = {
            "user_001": [
                {
                    "record_id": "REC_001_20240115",
                    "date": "2024-01-15",
                    "diagnosis": "上呼吸道感染",
                    "treatment": "口服阿莫西林3天，布洛芬退热，多休息多饮水",
                    "doctor": "张医生",
                    "department": "呼吸内科"
                },
                {
                    "record_id": "REC_001_20230820",
                    "date": "2023-08-20",
                    "diagnosis": "支气管炎",
                    "treatment": "阿奇霉素抗感染，氨溴索祛痰，雾化吸入布地奈德",
                    "doctor": "张医生",
                    "department": "呼吸内科"
                }
            ],
            "user_002": [
                {
                    "record_id": "REC_002_20240201",
                    "date": "2024-02-01",
                    "diagnosis": "高血压2级",
                    "treatment": "氨氯地平5mg每日一次，低盐饮食，定期监测血压",
                    "doctor": "王医生",
                    "department": "心血管内科"
                },
                {
                    "record_id": "REC_002_20231015",
                    "date": "2023-10-15",
                    "diagnosis": "冠状动脉粥样硬化",
                    "treatment": "阿司匹林肠溶片100mg/日，阿托伐他汀20mg/晚，低脂饮食",
                    "doctor": "赵医生",
                    "department": "心血管内科"
                }
            ],
            "user_003": [
                {
                    "record_id": "REC_003_20240310",
                    "date": "2024-03-10",
                    "diagnosis": "2型糖尿病",
                    "treatment": "二甲双胍500mg每日两次，控制饮食，适量运动，定期监测血糖",
                    "doctor": "孙医生",
                    "department": "内分泌科"
                },
                {
                    "record_id": "REC_003_20231128",
                    "date": "2023-11-28",
                    "diagnosis": "糖尿病足溃疡（左足）",
                    "treatment": "清创换药，胰岛素泵控糖，抗感染，改善微循环",
                    "doctor": "周医生",
                    "department": "内分泌科"
                }
            ],
            "user_004": [
                {
                    "record_id": "REC_004_20240520",
                    "date": "2024-05-20",
                    "diagnosis": "慢性胃炎伴幽门螺杆菌感染",
                    "treatment": "四联疗法根除HP：奥美拉唑+克拉霉素+阿莫西林+铋剂，疗程14天",
                    "doctor": "李医生",
                    "department": "消化内科"
                },
                {
                    "record_id": "REC_004_20230605",
                    "date": "2023-06-05",
                    "diagnosis": "胃食管反流病",
                    "treatment": "雷贝拉唑20mg/日，睡前抬高床头，避免睡前进食",
                    "doctor": "李医生",
                    "department": "消化内科"
                }
            ],
            "user_005": [
                {
                    "record_id": "REC_005_20240418",
                    "date": "2024-04-18",
                    "diagnosis": "过敏性哮喘急性发作",
                    "treatment": "沙丁胺醇雾化吸入，口服泼尼松3天，布地奈德/福莫特罗长期吸入",
                    "doctor": "陈医生",
                    "department": "呼吸内科"
                },
                {
                    "record_id": "REC_005_20231012",
                    "date": "2023-10-12",
                    "diagnosis": "过敏性鼻炎",
                    "treatment": "氯雷他定10mg/日，糠酸莫米松鼻喷，避免接触花粉等过敏原",
                    "doctor": "刘医生",
                    "department": "耳鼻喉科"
                }
            ]
        }
    
    def get_medical_records(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户医疗记录，若用户无特定记录则返回通用示例数据"""
        if user_id in self.records_db:
            return self.records_db[user_id]
        
        logger.info(f"用户 {user_id} 无特定记录，返回通用示例数据")
        return [
            {
                "record_id": f"REC_{user_id}_20240315",
                "date": "2024-03-15",
                "diagnosis": "上呼吸道感染",
                "treatment": "口服头孢克肟3天，布洛芬退热，多饮水多休息",
                "doctor": "张医生",
                "department": "呼吸内科"
            },
            {
                "record_id": f"REC_{user_id}_20231205",
                "date": "2023-12-05",
                "diagnosis": "急性胃肠炎",
                "treatment": "口服蒙脱石散止泻，补充电解质，清淡饮食",
                "doctor": "李医生",
                "department": "消化内科"
            }
        ]


# 全局数据库实例
db = MedicalRecordDatabase()


@mcp.tool()
def get_medical_records(user_id: Union[str, int]) -> List[Dict[str, Any]]:
    """
    获取患者的历史医疗记录，若无特定记录则返回通用示例数据
    
    Args:
        user_id: 患者ID
        
    Returns:
        医疗记录列表，包含诊断、治疗等信息
    """
    user_id = str(user_id)
    logger.info(f"收到查询请求: user_id={user_id}")
    
    try:
        records = db.get_medical_records(user_id)
        logger.info(f"返回 {len(records)} 条记录")
        return records
    except Exception as e:
        logger.error(f"查询失败: {str(e)}")
        raise


if __name__ == "__main__":
    # 启动MCP Server（使用stdio传输）
    logger.info("启动MCP Server...")
    mcp.run(transport="stdio")
