from fastapi import FastAPI
from app.web.chat_router.chat_router import chat_router
from app.web.websocket_router.websocket_test import ws_router
from app.web.websocket_router.vosk_router import vosk_router
from app.web.default_page_router.default_page_router import default_page_router
from fastapi.staticfiles import StaticFiles
import uvicorn
from pathlib import Path
from contextlib import asynccontextmanager
from app.ai.agent.multi_agent.graph.exam_graph import  ExamGraph
from langgraph.checkpoint.memory import InMemorySaver
#定义异步上下文管理器
@asynccontextmanager
async def content_manager(app:FastAPI):
    memory =InMemorySaver()

    app.state.exam_agent = ExamGraph(memory)
    print("AI模拟面试智能体创建成功")
    yield
    #消耗对象
    app.state.exam_agent = None
    print("AI模拟面试智能体关闭成功")

app = FastAPI(lifespan=content_manager)
#注册路由
app.include_router(chat_router)
app.include_router(ws_router)
app.include_router(vosk_router)

app.include_router(default_page_router)

#配置静态资源访问目录（基于当前文件定位，避免受启动时的 cwd 影响）
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "html"
app.mount("/static",StaticFiles(directory=str(STATIC_DIR)),name="static")

if __name__ =="__main__":
    uvicorn.run(app,host="localhost",port=8005)