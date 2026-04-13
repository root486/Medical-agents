"""
医疗辅助诊断系统 - 数据模型定义
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class DiagnosisStatus(str, Enum):
    """诊断流程状态枚举"""
    PENDING = "pending"  # 待处理
    TASK_SUMMARY = "task_summary"  # 任务汇总
    FETCHING_RECORDS = "fetching_records"  # 获取历史记录
    PRELIMINARY_DIAGNOSIS = "preliminary_diagnosis"  # 初步诊断
    CONSULTATION_DECISION = "consultation_decision"  # 会诊决策
    CROSS_DEPARTMENT = "cross_department"  # 跨科室会诊
    DOCTOR_REVIEW = "doctor_review"  # 医生复诊
    FINAL_SUMMARY = "final_summary"  # 最终汇总
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败


class UserSymptoms(BaseModel):
    """用户症状输入"""
    user_id: Optional[str] = Field(None, description="用户ID（可选，后端自动生成）")
    name: str = Field(..., description="患者姓名")
    symptoms: str = Field(..., description="症状描述")
    age: int = Field(..., description="年龄")
    gender: str = Field(..., description="性别")
    medical_history: Optional[str] = Field(None, description="既往病史")


class MedicalRecord(BaseModel):
    """医疗记录"""
    record_id: str
    date: str
    diagnosis: str
    treatment: str
    doctor: str
    department: str


class FinalReport(BaseModel):
    """最终诊断报告"""
    task_id: str
    user_id: str
    symptoms: str
    medical_records: List[Dict[str, Any]] = []
    preliminary_diagnosis: Optional[Dict[str, Any]] = None
    consultation_result: Optional[Dict[str, Any]] = None
    final_diagnosis: str = ""
    treatment_plan: str = ""
    doctor_notes: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    status: str = "pending"


class TaskStatus(BaseModel):
    """任务状态响应"""
    task_id: str
    status: str
    current_node: str
    progress: int  # 进度百分比
    message: str
    timeline: List[Dict[str, Any]] = []
    medical_records: List[Dict[str, Any]] = []
    preliminary_diagnosis: Optional[Dict[str, Any]] = None
    consultation_result: Optional[Dict[str, Any]] = None


class ConsultationRequest(BaseModel):
    """会诊确认请求"""
    task_id: str
    need_consultation: bool = Field(..., description="是否需要会诊")
    departments: Optional[List[str]] = Field(None, description="会诊科室列表")


class ReviewRequest(BaseModel):
    """医生复诊修改请求"""
    task_id: str
    modified_diagnosis: str = Field(..., description="修改后的诊断")
    modified_treatment: str = Field(..., description="修改后的治疗方案")
    doctor_notes: str = Field("", description="医生备注")


class GraphNode(BaseModel):
    """流程图节点"""
    id: str
    label: str
    type: str  # start, end, process, decision, parallel
    position: Dict[str, int]


class GraphEdge(BaseModel):
    """流程图边"""
    source: str
    target: str
    label: Optional[str] = None
    condition: Optional[str] = None


class GraphStructure(BaseModel):
    """流程图结构"""
    nodes: List[GraphNode]
    edges: List[GraphEdge]


