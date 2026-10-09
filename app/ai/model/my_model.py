from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

from vosk import Model

#读取配置文件
load_dotenv()
"""
基于单例模式的模型封装
"""
class MyModel:
    #定义私有属性
    _model = None
    #定义本地模型私有属性
    _local_model=None
    # 定义语音模型
    _vosk_model = None
    #定义静态函数,在线模型
    @staticmethod
    def get_model():
        #判断_model 是否未空
        if MyModel._model is None:
            #创建模型
            MyModel._model = ChatOpenAI(
                model= os.getenv("MODEL_LINE_NAME"),
                api_key=os.getenv("DASHSCOPE_API_KEY"),
                streaming=True,#开启流式输出
                extra_body={
                    "enable_thinking": False# 是否开启思考过程
                }
            )
        return MyModel._model
    #本地模型创建
    @staticmethod
    def get_local_model():
        #判断_model 是否未空
        if MyModel._local_model is None:
            #创建模型
            MyModel._local_model = ChatOpenAI(
                model= os.getenv("MODEL_LOCAL_NAME"),
                #Ollama 的 OpenAI 兼容接口并不校验密钥,但 openai SDK 要求 api_key 非空,
                #否则直接抛 Missing credentials,连请求都发不出去
                api_key="ddd",
                base_url=os.getenv("LOCAL_URL"),
                streaming=True,#开启流式输出
                # extra_body={
                #     "enable_thinking": False # 是否开启思考过程
                # }
            )
        return MyModel._local_model

        # 加载语音模型
    @staticmethod
    def get_vosk_model():
            # 判断_model 是否未空
        if MyModel._vosk_model is None:
                # 创建模型
            model_path = os.getenv("VOSK_PATH")
                # 加载模型
            MyModel._vosk_model = Model(model_path=model_path)
        return MyModel._vosk_model

if __name__ =="__main__":
    model = MyModel.get_local_model()
    rs = model.invoke("你好")
    print(rs)

