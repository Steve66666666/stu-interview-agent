from app.ai.tool.send_email_tool import send_email_tool
from app.ai.model.my_model import MyModel
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
import asyncio #异步执行库
#演示智能体创建
async def test_agent(q):
    # 1 创建一个大模型
    model = MyModel.get_local_model()
    #2 创建一个工具
    tools=[send_email_tool]
    #3 创建提示词,系统提示词
    prompt = """
       一 角色:  你是一个邮件发送助手
    """
    #4 创建智能体
    agent =create_agent(
        model =model,
        tools =tools,
        system_prompt=prompt,
        #debug=True #可选参数，一般用于调试，生成环境必须设置未false
    )
    #5 提问

    human_msg = {"messages": [HumanMessage(content=q)]}

    async for c,m in agent.astream(human_msg,stream_mode="messages"):
        #print(m)
        if c.content:
            yield c.content

#测试大模型的异步流式输出
async def test_create_model(q):
    # 1 创建一个大模型
    model = MyModel.get_local_model()
    #异步流式
    async for c in model.astream(input=q):
        if c.content:
            yield c.content


if __name__ =="__main__":
    q="请给2584744108@qq.com 发送一封邮件，通知他来上课"

    async def test():
        # 运行异步函数
        async  for rs in test_create_model(q):
            print(rs,end="")
    asyncio.run(test())

