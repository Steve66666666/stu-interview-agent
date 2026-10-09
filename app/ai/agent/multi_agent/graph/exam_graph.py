from app.ai.agent.multi_agent.state.exam_state import ExamState
from app.ai.agent.multi_agent.node.intent_node import intent_node
from app.ai.agent.multi_agent.node.question_node import question_node
from app.ai.agent.multi_agent.node.manager_node import manager_node
from app.ai.agent.multi_agent.node.answer_node import answer_node
from app.ai.agent.multi_agent.node.evaluate_node import evaluate_node
from app.ai.agent.multi_agent.node.reset_node import reset_node
from langgraph.graph import StateGraph,START,END
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
"""
模拟面试智能体
"""
class ExamGraph:

    def __init__(self,checkpoint):
        self.memory = checkpoint
        self.agent = self.get_agent()


   #构建图
    def get_agent(self):
        graph = StateGraph(ExamState)
        #添加节点
        graph.add_node("intent",intent_node)
        graph.add_node("question",question_node)
        graph.add_node("manager", manager_node)
        graph.add_node("answer", answer_node)
        graph.add_node("evaluate", evaluate_node)
        #评价后重新开局的清空节点
        graph.add_node("reset", reset_node)

        #画边:所有业务节点执行完都回到 manager,由 manager 决定下一跳
        graph.add_edge(START,"manager")
        graph.add_edge("intent","manager")
        graph.add_edge("question","manager")
        graph.add_edge("answer", "manager")
        graph.add_edge("evaluate", "manager")
        graph.add_edge("reset", "manager")

        #编译
        self.agent = graph.compile(checkpointer=self.memory)
        return self.agent
    #对话
    async def chat(self,question,user_id,session_id):
        print(f"进入聊天:用户问题：{question},用户ID:{user_id},会话ID:{session_id}")
        #构建用户问题
        user_msg ={"messages":[HumanMessage(content=question)]}
        #配置检测点
        config = {"configurable":{"thread_id":session_id}}
        #采用异步流式,同时监听 messages(上屏内容) 和 custom(评价节点的实时输出)
        async for c,m in self.agent.astream(user_msg,config,stream_mode=["messages","custom"]):
              if c =="messages":
                  messages,meta = m
                  #过滤空片段,避免前端收到一堆空串
                  if messages.content:
                      yield messages.content
              else:
                  yield m


    #画图
    def draw(self):
        data = self.agent.get_graph().draw_mermaid_png()
        with open("考试图2.png","wb") as f:
            f.write(data)
if __name__ =="__main__":
    memory = MemorySaver()
    exam_graph = ExamGraph(checkpoint=memory)
    exam_graph.draw()
