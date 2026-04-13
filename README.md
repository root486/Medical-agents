# 医疗辅助诊断多智能体Agent系统

基于 **LangGraph + FastAPI + Vue3** 的医疗辅助诊断系统，通过多智能体协作工作流实现从症状录入到诊断报告生成的完整流程。纯本地部署，无需 Docker。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI + Uvicorn |
| AI 编排 | LangGraph 状态图 + SubGraph 子图 |
| LLM | 通义千问（DashScope API） |
| Agent | LangChain ReAct Agent（工具调用） |
| RAG | Chroma 向量数据库 + 通义千问 Embedding |
| MCP | Model Context Protocol（stdio 传输） |
| 关系数据库 | MySQL（SQLAlchemy + PyMySQL） |
| 任务持久化 | SQLite |
| 前端 | Vue 3 + Vite + Element Plus + Pinia |

## 核心能力

- **LangGraph 状态图**：7 个节点的完整诊断工作流，条件路由控制会诊分支
- **Human-In-Loop**：通过 `interrupt()` + `Command(resume=...)` 实现医生在会诊决策和复诊两个节点的人工介入
- **ReAct Agent**：初步诊断节点使用 `create_react_agent` 创建工具调用 Agent，自主决定是否搜索知识库、查询患者历史
- **SubGraph 子图**：跨科室会诊动态构建子图，每个科室对应一个独立的 ReAct Agent 节点，最终汇入共识生成节点
- **RAG 检索**：Chroma 本地持久化向量库存储医疗知识，通义千问 Embedding 模型生成向量
- **MCP 协议**：通过 FastMCP 实现 stdio 传输的 MCP Server，提供患者历史记录查询工具
- **Time Travel**：利用 LangGraph 的 `update_state(as_node=...)` 实现状态回溯到任意节点
- **Memory 管理**：短期记忆（进程内存）+ 长期记忆（Chroma 向量库持久化）

## 项目结构

```
yiliao/
├── backend/
│   ├── main.py                 # FastAPI 主应用，启动入口
│   ├── config.py               # 配置管理（pydantic-settings）
│   ├── api_routes.py           # API 路由，所有接口定义
│   ├── models.py               # Pydantic 数据模型
│   ├── db_models.py            # SQLAlchemy ORM 模型
│   ├── database.py             # MySQL 数据库连接配置
│   ├── task_store.py           # SQLite 任务状态持久化
│   ├── diagnosis_graph.py      # LangGraph 诊断流程图（主图）
│   ├── consultation_subgraph.py # 跨科室会诊子图（SubGraph）
│   ├── agent_tools.py          # ReAct Agent 工具集
│   ├── llm_service.py          # LLM 服务（最终报告生成）
│   ├── rag_module.py           # RAG 检索模块（Chroma）
│   ├── mcp_client.py           # MCP 客户端
│   ├── mcp_server.py           # MCP Server（FastMCP）
│   ├── memory_manager.py       # 记忆管理（短期+长期）
│   ├── requirements.txt        # Python 依赖
│   ├── .env                    # 环境变量
│   └── knowledge_base/
│       └── common_diseases.txt # 医疗知识库（TXT）
├── frontend/
│   ├── src/
│   │   ├── main.js             # Vue 入口
│   │   ├── App.vue             # 根组件
│   │   ├── router/index.js     # 路由配置
│   │   ├── stores/diagnosis.js # API 封装
│   │   ├── utils/api.js        # Axios 配置
│   │   └── views/
│   │       ├── DiagnosisPage.vue  # 诊断主页面
│   │       ├── ReportPage.vue     # 诊断报告页
│   │       └── TimelinePage.vue   # 流程回溯页
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
└── README.md
```

## LangGraph 流程图

```
START
  │
  ▼
┌─────────────┐
│  任务汇总    │
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│ 获取历史记录(MCP) │
└──────┬───────────┘
       │
       ▼
┌───────────────────────┐
│ 初步诊断(ReAct Agent) │  ← RAG 知识检索 + 患者历史查询
└──────┬────────────────┘
       │
       ▼
┌────────────────────────────┐
│ 会诊决策(interrupt, HITL)  │  ← 医生决定是否会诊
└──────┬─────────┬───────────┘
       │         │
  需要会诊    不需要
       │         │
       ▼         │
┌────────────┐   │
│ 跨科室会诊  │   │  ← SubGraph：每个科室一个 ReAct Agent
│ (SubGraph) │   │
└──────┬─────┘   │
       │         │
       ▼         ▼
┌──────────────────────────┐
│ 医生复诊(interrupt, HITL) │  ← 医生修改诊断和治疗方案
└──────┬───────────────────┘
       │
       ▼
┌──────────────┐
│ 最终报告生成  │  ← LLM 整合所有信息
└──────┬───────┘
       │
       ▼
      END
```

## 快速开始

### 前置要求

- Python 3.13+
- Node.js 18+
- MySQL 数据库（创建 `yiliao` 数据库）
- 通义千问 API Key

### 后端启动

```bash
cd backend
pip install -r requirements.txt
# 编辑 .env 填入 DASHSCOPE_API_KEY
python main.py
```

后端运行在 `http://localhost:8000`，API 文档 `http://localhost:8000/docs`

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

前端运行在 `http://localhost:3000`

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/start-diagnosis` | 启动诊断流程 |
| GET  | `/api/status/{task_id}` | 获取任务状态与进度 |
| POST | `/api/consult/confirm` | 医生确认会诊决策（resume） |
| POST | `/api/review/modify` | 医生提交修改诊断（resume） |
| GET  | `/api/report/{task_id}` | 获取最终诊断报告 |
| GET  | `/api/timeline/{task_id}` | 获取流程回溯时间线 |
| POST | `/api/rewind/{task_id}` | Time Travel 回溯到指定节点 |
| GET  | `/api/graph/structure` | 获取流程图结构（前端可视化） |
| GET  | `/api/users` | 查询已有患者列表 |
| GET  | `/api/memory/{user_id}` | 获取用户记忆摘要 |
| POST | `/api/knowledge/load` | 重新加载医疗知识库 |
| GET  | `/api/mcp/config` | 获取 MCP 配置信息 |

## 使用流程

1. 打开前端页面，录入患者信息和症状描述，点击「开始诊断」
2. 系统自动执行：任务汇总 → MCP 获取历史记录 → ReAct Agent 初步诊断
3. 流程暂停在「会诊决策」节点，医生选择是否需要跨科室会诊
4. 若会诊，系统运行 SubGraph 子图生成各科室意见和共识
5. 流程暂停在「医生复诊」节点，医生审查并修改诊断结果和治疗方案
6. 医生可选择 Time Travel 回溯到会诊决策节点重新选择
7. 提交后系统生成最终诊断报告，可查看报告和流程时间线
