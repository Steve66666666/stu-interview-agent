from langchain_core.messages import HumanMessage, AIMessage

from app.ai.agent.multi_agent.state.exam_state import ExamState

"""
答题节点：收集用户答案。每答一题立即进入评价,所以这里不再判断题量是否答满。
"""
def answer_node(state:ExamState):
    #取最后一条"用户消息",而不是简单取 messages[-1]。
    #因为答题路径是 question -> intent -> answer,intent_node 会追加一条 AIMessage,
    #此时 messages[-1] 是 AI 消息,若直接取它会导致用户的答案被静默丢弃。
    user_input = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            user_input = msg.content
            break

    if user_input is None:
        #确实没有用户输入,保持原状态,否则会把 question 状态冲掉导致重复出同一题
        return {
            "messages": [AIMessage(content="\n不是用户输入\n")],
        }

    #获取当前题目的编号与题面
    question_id = state.get("question_id")
    question_name = state.get("current_question","")
    #获取用户答案列表
    user_answer_list = list(state.get("user_answer_list") or [])
    #记录答案。带上题目正文,便于评价时把答案和题目对上,
    #不会因为题目序号错位而张冠李戴。
    user_answer_list.append(
        {"id":question_id,"question":question_name,"answer":user_input}
    )
    print(f"已记录第{state.get('current',0)}题的答案,进入评价")
    return {
        "messages":[AIMessage(content="\n答案已经记录\n")],
        "user_answer_list":user_answer_list,
        "exam_step":"answer",
        #每题答完立即评价,固定进入评价节点
        "continue_question":False
    }
