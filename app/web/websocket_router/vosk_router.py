# app/web/websocket_router/vosk_router.py  —— 语音识别 WebSocket 路由
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ai.agent.vosk_agent import VoskAgent

vosk_router = APIRouter()


@vosk_router.websocket("/vosk")
async def vosk_endpoint(ws: WebSocket):
    await ws.accept()                       # WebSocket 握手，必须第一步
    agent = VoskAgent.get_vosk()            # 复用单例（模型加载很重）
    try:
        await agent.speak(ws)               # 循环收音 + 推送识别结果
    except WebSocketDisconnect:
        print("语音连接已断开")
    finally:
        agent.listing = False               # 确保停止收音循环
