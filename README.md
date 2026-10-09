# stu-interview-agent · AI 多智能体模拟面试平台

基于 **FastAPI + LangGraph** 的 AI 模拟面试平台：由 Manager 节点统一调度，按「意图识别 → 出题 → 答题 → 逐题评分 → 报告」的流程完成一场面试，前端通过 SSE 实时上屏，并集成 **Vosk 离线语音识别**（WebSocket）把语音转成问题自动提交。

## 功能

- **多智能体答题流程**：`StateGraph` 六个节点（Manager / Intent / Question / Answer / Evaluate / Reset），所有业务节点执行完回到 Manager，由 Manager 用 `Command(goto=...)` 决定下一跳。
- **按课程随机出题**：`ORDER BY RAND() LIMIT 1` + 排除已出过的题 + 抽空兜底。
- **60 / 25 / 15 逐题即时评分**：评价节点内按三部分打分并生成报告。
- **双通道流式输出**：`astream(stream_mode=["messages","custom"])` —— `messages` 通道推上屏文字，`custom` 通道（`get_stream_writer()`）推评价报告片段。
- **多会话隔离**：`thread_id = session_id` + `InMemorySaver` 检查点，多用户 / 多会话互不干扰。
- **Vosk 离线语音识别**：前端点「开启语音」→ 连 WebSocket `/vosk` → 后端循环收音、识别结果推回前端并自动发送。全程离线，数据不出本机。

## 技术栈

| 层 | 选型 |
|---|---|
| Web 框架 | FastAPI + Uvicorn |
| 智能体编排 | LangGraph（StateGraph / Command / 检查点） |
| 模型 | LangChain + `langchain-openai`（在线 Qwen、本地 Ollama 双通道） |
| 流式 | SSE（`StreamingResponse`）+ WebSocket |
| 语音 | Vosk（`vosk-model-cn-0.22`）+ PyAudio |
| 前端 | Vue 2（全局构建）+ marked.js |
| 存储 | MySQL（题库 / 用户） |

## 目录结构

```
app/
├── main.py                        # 应用入口（端口 8005）、路由注册、生命周期
├── ai/
│   ├── agent/
│   │   ├── vosk_agent.py          # 语音识别单例（模型加载很重）
│   │   └── multi_agent/
│   │       ├── graph/exam_graph.py        # 面试状态图
│   │       ├── node/                      # manager / intent / question / answer / evaluate / reset
│   │       └── state/exam_state.py        # ExamState（TypedDict + reducer）
│   ├── model/my_model.py          # 在线 / 本地 / 语音 三类模型的单例封装
│   ├── prompt/                    # 提示词与 yaml（intent_node.yaml / evaluate_node.yaml）
│   └── tool/                      # MySQL、邮件等工具
├── web/
│   ├── chat_router/chat_router.py              # GET /chat → SSE
│   ├── websocket_router/websocket_test.py      # WS /ws（demo）
│   ├── websocket_router/vosk_router.py         # WS /vosk（语音识别）
│   └── default_page_router/                    # / → /static/chat.html
├── html/                          # 前端页面（chat.html / login.html / test.html）
└── test/                          # 语音、WebSocket、智能体自测脚本
```

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 重定向到 `/static/chat.html` |
| GET | `/chat?question=&user_id=&session_id=` | SSE 流式问答，`data: {"data": "...", "done": false}` |
| WS | `/ws` | 双向通讯 demo |
| WS | `/vosk` | 语音识别：连接后服务端先推 `开始说话`，随后推送识别文本 |

## 快速开始

```bash
# 1. 依赖
pip install -r requirements.txt

# 2. 环境变量：复制一份 .env 并填入自己的配置
#    需要的主要变量（键名）：
#      MODEL_LINE_NAME / DASHSCOPE_API_KEY        —— 在线模型
#      MODEL_LOCAL_NAME / LOCAL_URL               —— 本地 Ollama
#      DB_HOST / DB_PORT / DB_USER / DB_PASSWORD / DB_NAME   —— MySQL 题库
#      VOSK_PATH                                  —— Vosk 模型目录，如 D:\models\vosk-model-cn-0.22
#      EMAIL_* / AMAP_KEY / CHROMA_PATH / EMBEDDING_MODEL_PATH ...

# 3. Vosk 中文模型（离线，需自行下载解压并把路径写进 VOSK_PATH）
#    https://alphacephei.com/vosk/models  →  vosk-model-cn-0.22

# 4. 启动（在仓库根目录执行）
python -m app.main        # http://localhost:8005
```

> `.env` 含数据库密码与 API Key，已在 `.gitignore` 中排除，**不要提交到仓库**。

## 语音链路说明

```
前端 chat.html  --WebSocket-->  /vosk  -->  vosk_router.vosk_endpoint
                                              │  agent = VoskAgent.get_vosk()   # 复用单例，模型加载很重
                                              ▼
                                         VoskAgent.speak(ws)
                                           ├─ 推「开始说话」→ 前端禁用按钮
                                           ├─ PyAudio 16kHz 单声道录音（read 放线程池，避免阻塞事件循环）
                                           ├─ KaldiRecognizer 识别出文本 → 推送
                                           └─ 前端填入输入框并自动发送（走 SSE /chat）
```

要点：

- `KaldiRecognizer` 的采样率必须与 PyAudio 开门时的 `rate` 一致（都是 16000），否则识别乱码。
- 模型加载很重 → `VoskAgent.get_vosk()` 单例缓存。
- `pyaudio.Stream.read` 是阻塞调用，放在 `run_in_executor` 里执行，避免卡死 FastAPI 事件循环。
- `read(..., exception_on_overflow=False)`：麦克风缓冲区溢出时返回空数据，而不是抛 `OSError`。

## 自测

```bash
python -m app.test.test_vosk          # 直接用麦克风跑一遍 Vosk 识别
python -m app.test.test_websocket     # WebSocket 连通性
```

更多实现细节与知识点见 [多智能体模拟面试平台核心代码与知识点详解.md](./多智能体模拟面试平台核心代码与知识点详解.md)。
