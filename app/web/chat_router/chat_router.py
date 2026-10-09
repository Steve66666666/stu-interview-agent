from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import json
import traceback
chat_router = APIRouter()


#聊天接口
@chat_router.get("/chat")
async def chat(request: Request, question: str, user_id: str, session_id: str = None):
    print(f"用户问题:{question},用户ID:{user_id},会话ID:{session_id}")
    #从应用生命周期中取出已经构建好的模拟面试图智能体
    exam_agent = getattr(request.app.state, "exam_agent", None)
    if exam_agent is None:
        #兜底:应用尚未完成启动或已被销毁
        async def empty():
            data = {"data": "面试智能体尚未就绪,请稍后重试", "done": True}
            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
        return StreamingResponse(empty(), media_type="text/event-stream")
    #会话ID兜底,保证检查点始终有可用的 thread_id
    if not session_id:
        session_id = user_id

    # 定义一个异步迭代器
    async def generate(question, user_id, session_id):
        try:

            async for x in exam_agent.chat(question, user_id, session_id):
                # False 流式未结束
                data = {"data": x, "done": False}
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            # 流式结束
            data = {"data": "", "done": True}
            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        except Exception as e:
            #打印完整堆栈,否则前端只看到一句"流式异常",无法定位真正原因
            traceback.print_exc()
            # 流式结束
            data = {"data": f"流式异常: {e}", "done": True}
            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(question, user_id, session_id), media_type="text/event-stream")
