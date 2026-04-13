"""
FastAPI 路由模块
全部操作通过 LangGraph 引擎执行，使用 interrupt() + Command(resume=...) 实现 Human-In-Loop
"""
from fastapi import APIRouter, HTTPException
import uuid
import logging
from datetime import datetime
from threading import Thread

from langgraph.types import Command
from models import (
    UserSymptoms, ConsultationRequest, ReviewRequest,
    TaskStatus, FinalReport, GraphStructure, GraphNode, GraphEdge
)
from diagnosis_graph import diagnosis_graph
from rag_module import knowledge_base
from mcp_client import mcp_server
from memory_manager import memory_manager
from database import SessionLocal
from db_models import UserProfile
from task_store import task_store_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["diagnosis"])


def _run_graph_and_save(task_id: str, graph_input, config: dict):
    """
    通用：流式执行 LangGraph 并保存每一步状态。
    图会在 interrupt() 或 END 处自动停止。
    """
    try:
        for event in diagnosis_graph.stream(graph_input, config, stream_mode="values"):
            current_state = dict(event)
            task_store_db.save_task(task_id, current_state)
            logger.info(f"任务 {task_id} - 执行到节点: {current_state.get('current_node')}")

        graph_state = diagnosis_graph.get_state(config)
        if graph_state.next:
            waiting_node = graph_state.next[0]
            logger.info(f"任务 {task_id} 在 {waiting_node} 节点 interrupt，等待人工输入")
            task = task_store_db.get_task(task_id)
            if task:
                task["current_node"] = waiting_node
                task["status"] = waiting_node
                task_store_db.save_task(task_id, task)
        else:
            logger.info(f"任务 {task_id} 图执行完毕")

    except Exception as e:
        logger.error(f"任务 {task_id} LangGraph 执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        failed_state = task_store_db.get_task(task_id) or {}
        failed_state["status"] = "failed"
        failed_state["error"] = str(e)
        task_store_db.save_task(task_id, failed_state)


def _generate_user_id(db) -> str:
    """自动生成患者编号：P + 日期 + 3位序号，如 P20260411001"""
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"P{today}"
    last = (
        db.query(UserProfile)
        .filter(UserProfile.user_id.like(f"{prefix}%"))
        .order_by(UserProfile.user_id.desc())
        .first()
    )
    if last:
        seq = int(last.user_id[-3:]) + 1
    else:
        seq = 1
    return f"{prefix}{seq:03d}"


@router.get("/users")
async def list_users():
    """查询已有患者列表，供前端下拉选择"""
    db = SessionLocal()
    try:
        profiles = (
            db.query(UserProfile)
            .order_by(UserProfile.updated_at.desc())
            .limit(50)
            .all()
        )
        return [
            {
                "user_id": p.user_id,
                "name": p.name,
                "gender": p.gender,
                "age": p.age,
                "medical_history": p.medical_history or "",
            }
            for p in profiles
        ]
    finally:
        db.close()


@router.post("/start-diagnosis")
async def start_diagnosis(symptoms: UserSymptoms):
    """启动诊断流程 — 通过 LangGraph stream 执行，到 interrupt() 自动暂停"""
    db = SessionLocal()
    try:
        if symptoms.user_id:
            profile = db.query(UserProfile).filter(
                UserProfile.user_id == symptoms.user_id
            ).first()
            if not profile:
                raise HTTPException(status_code=404, detail=f"患者编号 {symptoms.user_id} 不存在")
            if symptoms.medical_history:
                profile.medical_history = symptoms.medical_history
            logger.info(f"使用现有患者档案: {profile.user_id} ({profile.name})")
        else:
            user_id = _generate_user_id(db)
            profile = UserProfile(
                user_id=user_id,
                name=symptoms.name,
                gender=symptoms.gender,
                age=symptoms.age,
                medical_history=symptoms.medical_history,
            )
            db.add(profile)
            logger.info(f"创建新患者档案: {user_id} ({symptoms.name})")
        db.commit()
        db.refresh(profile)

        task_id = str(uuid.uuid4())
        initial_state = {
            "task_id": task_id,
            "user_id": profile.user_id,
            "symptoms": symptoms.symptoms,
            "age": profile.age,
            "gender": profile.gender,
            "medical_history": profile.medical_history or "",
            "medical_records": [],
            "preliminary_diagnosis": None,
            "need_consultation": False,
            "consultation_departments": [],
            "consultation_result": None,
            "final_diagnosis": "",
            "treatment_plan": "",
            "doctor_notes": "",
            "current_node": "__start__",
            "status": "pending",
            "timeline": [],
            "human_approval": None,
        }

        task_store_db.save_task(task_id, initial_state)
        config = {"configurable": {"thread_id": task_id}}

        thread = Thread(
            target=_run_graph_and_save,
            args=(task_id, initial_state, config),
            daemon=True,
        )
        thread.start()

        return {
            "task_id": task_id,
            "user_id": profile.user_id,
            "patient_name": profile.name,
            "message": "诊断流程已启动",
            "status": "pending",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动诊断流程失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/status/{task_id}")
async def get_status(task_id: str):
    """获取当前流程节点与状态"""
    task = task_store_db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    progress_map = {
        "pending": 0,
        "task_summary": 10,
        "fetching_records": 25,
        "preliminary_diagnosis": 40,
        "consultation_decision": 50,
        "cross_department": 65,
        "doctor_review": 80,
        "final_summary": 90,
        "completed": 100
    }

    progress = progress_map.get(task["status"], 0)

    return TaskStatus(
        task_id=task_id,
        status=task["status"],
        current_node=task["current_node"],
        progress=progress,
        message=f"当前节点: {task['current_node']}",
        timeline=task.get("timeline", []),
        medical_records=task.get("medical_records", []),
        preliminary_diagnosis=task.get("preliminary_diagnosis"),
        consultation_result=task.get("consultation_result"),
    )


@router.post("/consult/confirm")
async def confirm_consultation(request: ConsultationRequest):
    """
    医生确认是否需要会诊 — 通过 Command(resume=...) 恢复 LangGraph 执行。
    若需要会诊则进入 cross_department_consultation，否则直接进入 doctor_review。
    """
    task = task_store_db.get_task(request.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    config = {"configurable": {"thread_id": request.task_id}}
    resume_value = {
        "need_consultation": request.need_consultation,
        "departments": request.departments or []
    }

    thread = Thread(
        target=_run_graph_and_save,
        args=(request.task_id, Command(resume=resume_value), config),
        daemon=True
    )
    thread.start()

    return {
        "message": "会诊确认已提交，LangGraph 继续执行中...",
        "need_consultation": request.need_consultation,
    }


@router.post("/review/modify")
async def modify_diagnosis(request: ReviewRequest):
    """
    医生修改/确认诊断 — 通过 Command(resume=...) 恢复 LangGraph 执行。
    图会自动继续经过 final_summary 到达 END。
    """
    task = task_store_db.get_task(request.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    config = {"configurable": {"thread_id": request.task_id}}
    resume_value = {
        "modified_diagnosis": request.modified_diagnosis,
        "modified_treatment": request.modified_treatment,
        "doctor_notes": request.doctor_notes
    }

    def run_resume_and_finalize():
        _run_graph_and_save(request.task_id, Command(resume=resume_value), config)

        final_state = task_store_db.get_task(request.task_id)
        if final_state and final_state.get("status") == "completed":
            try:
                memory_manager.save_long_term_memory(
                    user_id=final_state["user_id"],
                    diagnosis_data={
                        "symptoms": final_state.get("symptoms", ""),
                        "medical_history": final_state.get("medical_history", ""),
                        "preliminary_diagnosis": final_state.get("preliminary_diagnosis", {}),
                        "final_diagnosis": final_state.get("final_diagnosis", ""),
                        "treatment_plan": final_state.get("treatment_plan", ""),
                        "doctor_notes": final_state.get("doctor_notes", "")
                    }
                )
                memory_manager.add_short_term_memory(final_state["user_id"], {
                    "type": "diagnosis_completed",
                    "task_id": request.task_id,
                    "final_diagnosis": final_state.get("final_diagnosis", "")
                })
                logger.info(f"已为用户 {final_state['user_id']} 保存记忆")
            except Exception as e:
                logger.error(f"保存记忆失败: {str(e)}")

    thread = Thread(target=run_resume_and_finalize, daemon=True)
    thread.start()

    return {
        "message": "诊断修改已提交，LangGraph 继续执行最终汇总...",
        "task_id": request.task_id
    }


@router.get("/report/{task_id}")
async def get_report(task_id: str):
    """获取最终诊断报告"""
    task = task_store_db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="诊断流程尚未完成")

    return FinalReport(
        task_id=task_id,
        user_id=task["user_id"],
        symptoms=task["symptoms"],
        medical_records=task.get("medical_records", []),
        preliminary_diagnosis=task.get("preliminary_diagnosis"),
        consultation_result=task.get("consultation_result"),
        final_diagnosis=task.get("final_diagnosis", ""),
        treatment_plan=task.get("treatment_plan", ""),
        doctor_notes=task.get("doctor_notes", ""),
        status="completed"
    )


@router.get("/timeline/{task_id}")
async def get_timeline(task_id: str):
    """获取诊断流程执行时间线（各节点执行记录）"""
    task = task_store_db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return {
        "task_id": task_id,
        "timeline": task.get("timeline", []),
        "current_status": task["status"],
        "current_node": task["current_node"]
    }


@router.get("/graph/structure")
async def get_graph_structure():
    """获取流程图结构（用于前端可视化）"""
    nodes = [
        GraphNode(id="START", label="开始", type="start", position={"x": 400, "y": 50}),
        GraphNode(id="task_summary", label="诊断任务汇总", type="process", position={"x": 400, "y": 150}),
        GraphNode(id="fetch_medical_records", label="获取用户历史诊断记录\n(MCP调用)", type="process", position={"x": 200, "y": 300}),
        GraphNode(id="preliminary_diagnosis", label="参考指南，给出初步诊断结果\n(RAG检索)", type="process", position={"x": 600, "y": 300}),
        GraphNode(id="consultation_decision", label="是否需要跨科室会诊？\n(interrupt() Human-In-Loop)", type="decision", position={"x": 400, "y": 450}),
        GraphNode(id="cross_department_consultation", label="跨科室诊断\n(SubGraph子图)", type="process", position={"x": 200, "y": 600}),
        GraphNode(id="doctor_review", label="医生复诊\n(interrupt() Human-In-Loop)", type="process", position={"x": 600, "y": 600}),
        GraphNode(id="final_summary", label="诊断任务汇总\n(最终结果整合)", type="process", position={"x": 400, "y": 750}),
        GraphNode(id="END", label="结束\n(输出诊断报告)", type="end", position={"x": 400, "y": 900})
    ]

    edges = [
        GraphEdge(source="START", target="task_summary"),
        GraphEdge(source="task_summary", target="fetch_medical_records"),
        GraphEdge(source="fetch_medical_records", target="preliminary_diagnosis"),
        GraphEdge(source="preliminary_diagnosis", target="consultation_decision"),
        GraphEdge(source="consultation_decision", target="cross_department_consultation", label="需要会诊", condition="need_consultation=true"),
        GraphEdge(source="consultation_decision", target="doctor_review", label="不需要", condition="need_consultation=false"),
        GraphEdge(source="cross_department_consultation", target="doctor_review"),
        GraphEdge(source="doctor_review", target="final_summary"),
        GraphEdge(source="final_summary", target="END")
    ]

    return GraphStructure(nodes=nodes, edges=edges)


@router.get("/mcp/config")
async def get_mcp_config():
    """获取MCP配置示例"""
    return mcp_server.get_mcp_config()


@router.post("/knowledge/load")
async def load_knowledge_base():
    """加载医疗知识库"""
    try:
        knowledge_base.load_knowledge_base()
        return {"message": "知识库加载成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/{user_id}")
async def get_user_memory(user_id: str):
    """获取用户记忆摘要"""
    return memory_manager.get_user_memory_summary(user_id)


@router.post("/rewind/{task_id}")
async def rewind_to_node(task_id: str, target_node: str):
    """
    Time Travel - 回溯到会诊决策节点。
    利用 LangGraph 的 update_state(as_node="preliminary_diagnosis") 将图状态回退，
    清空会诊及后续结果，图从 preliminary_diagnosis 之后重新执行，
    在 consultation_decision 节点的 interrupt() 处暂停等待医生重新选择。
    """
    task = task_store_db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    valid_nodes = ["consultation_decision"]
    if target_node not in valid_nodes:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的回溯目标: {target_node}，只支持 {valid_nodes}"
        )

    logger.info(f"任务 {task_id} 请求回溯到节点: {target_node}")
    config = {"configurable": {"thread_id": task_id}}

    reset_values = {
        "consultation_result": None,
        "final_diagnosis": "",
        "treatment_plan": "",
        "doctor_notes": "",
        "need_consultation": False,
        "human_approval": None,
        "current_node": "preliminary_diagnosis",
        "status": "preliminary_diagnosis",
    }
    timeline_entry = {
        "timestamp": datetime.now().isoformat(),
        "node": "rewind",
        "status": "rewind",
        "message": f"医生回溯到会诊决策节点，请重新选择是否需要会诊"
    }
    reset_values["timeline"] = task.get("timeline", []) + [timeline_entry]

    diagnosis_graph.update_state(config, reset_values, as_node="preliminary_diagnosis")

    def run_rewind():
        _run_graph_and_save(task_id, None, config)

    thread = Thread(target=run_rewind, daemon=True)
    thread.start()

    logger.info(f"任务 {task_id} 已回溯到 {target_node}")

    return {
        "message": f"已回溯到 {target_node}，请重新选择是否需要会诊",
        "target_node": target_node,
        "current_node": "consultation_decision",
        "status": "consultation_decision"
    }
