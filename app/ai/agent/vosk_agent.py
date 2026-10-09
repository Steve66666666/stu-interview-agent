import asyncio
import json                              # 处理JSON格式的识别结果

import pyaudio                           # 音频输入输出库
from vosk import Model, KaldiRecognizer  # Vosk语音识别核心库

from fastapi import WebSocket

from app.ai.model.my_model import MyModel


class VoskAgent:
    _vosk = None

    def __init__(self):
        self.model = MyModel.get_vosk_model()
        self.stream = self.get_stream()
        self.re = KaldiRecognizer(self.model, 16000)
        # 是否正在说话
        self.listing = False

    # 定义静态函数
    @staticmethod
    def get_vosk():
        if VoskAgent._vosk is None:
            VoskAgent._vosk = VoskAgent()
            return VoskAgent._vosk
        return VoskAgent._vosk

    def get_stream(self):
        # ------------加载本地音频配置--------------
        p = pyaudio.PyAudio()  # 创建PyAudio实例管理音频设备

        self.stream = p.open(
            format=pyaudio.paInt16,  # 16位整数格式
            channels=1,              # 单声道
            rate=16000,              # 16kHz采样率（必须与 KaldiRecognizer 一致）
            input=True,              # 输入模式（录音）
            frames_per_buffer=4096   # 每个缓冲区4096帧
        )
        return self.stream

    def _read_chunk(self):
        """阻塞式读取一帧音频。

        pyaudio 的 read 是阻塞调用，放在线程池里执行避免卡死事件循环。
        exception_on_overflow=False：麦克风缓冲区溢出时返回空数据而不是抛 OSError。
        """
        return self.stream.read(4096, exception_on_overflow=False)

    # 开始说话业务
    async def speak(self, ws: WebSocket):
        await self.send_msg("开始说话", ws)
        # 每次进入都重建识别器，避免上一次会话的音频残留串到这一次
        self.re = KaldiRecognizer(self.model, 16000)
        # 开启语音
        self.listing = True
        # 开启音频
        self.stream.start_stream()
        loop = asyncio.get_running_loop()
        try:
            while self.listing:
                chunk = await loop.run_in_executor(None, self._read_chunk)
                if not chunk:
                    continue
                if self.re.AcceptWaveform(chunk):
                    rs = json.loads(self.re.Result())
                    if rs.get("text"):
                        await self.send_msg(rs["text"], ws)
        finally:
            # 无论正常结束还是异常断开，都要停掉收音
            self.listing = False
            try:
                self.stream.stop_stream()
            except Exception:
                pass

    # 信息推送和语音的关闭
    async def send_msg(self, text, ws: WebSocket):
        if "开始说话" in text:
            await ws.send_text(text)
            return
        else:
            await ws.send_text(text)
            # 停止语音
            self.listing = False
