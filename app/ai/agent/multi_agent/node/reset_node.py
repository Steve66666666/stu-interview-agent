from langchain_core.messages import AIMessage

from app.ai.agent.multi_agent.state.exam_state import ExamState

"""
重置节点：评价结束后用户重新要题时,清空上一轮的题目与答案,开启新一轮面试。
LangGraph 的 reducer 会合并状态,所以清空必须显式赋空列表,不能靠"不返回该字段"。
"""
def reset_node(state:ExamState):
    print("重置上一轮进度,开启新一轮出题")
    #保留历史评价:每题答完都会产出一份评价,这些结论不能因为开新一轮就被抹掉,
    #否则用户拿不到整场的完整报告。
    history = state.get("evaluation") or ""
    return {
        #清空题目、标准答案、用户答案与本轮题目进度
        "questions":[],
        "sure_answer":[],
        "user_answer_list":[],
        "current":0,
        "question_id":None,
        "current_question":"",
        "continue_question":True,
        #历史评价原样保留
        "evaluation":history,
        #重置动作已完成
        "need_reset":False,
        "exam_step":"reset"
    }