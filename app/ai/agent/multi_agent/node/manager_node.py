from app.ai.agent.multi_agent.state.exam_state import ExamState
from langgraph.types import Command
from langgraph.graph import END
from langchain_core.messages import HumanMessage

"""
主管节点，中枢，负责调用其他节点
"""
def manager_node(state:ExamState):
    #获取是否继续出题
    continue_question = state.get("continue_question",True)
    #获取考试状态
    exam_state = state.get("exam_step","start")
    #本轮意图识别结果:answer=用户在答题 add=用户要追加题目
    user_action = state.get("user_action")
    #获取最后一条消息
    last_msg = state["messages"][-1]
    #判断本轮是否由用户发起。用标志位而不是拿消息内容做判断,
    #因为用户完全可能回答空字符串,那样会被误判成"等待输入"
    is_user_turn = isinstance(last_msg, HumanMessage)
    print(f"当前考试状态:{exam_state}  本轮意图:{user_action}  是否用户输入:{is_user_turn}")

    if exam_state == "start":
        #首次进入,先识别意图
        return Command(goto="intent")

    elif exam_state == "intent":
        #意图识别完成,统一进入出题节点。
        #注意:这里不能判断 user_action 再决定去 answer。
        #答题轮也会经过 intent_node 做意图判定,
        #如果这里把 action=answer 的轮次直接送去 answer,就会跳过 question 节点,
        #导致同一道题被重复收两次答案。
        #所以只处理"需要出题"的情况:首次出题、或用户明确要求追加。
        if user_action == "add":
            print("用户要求出题")
            #上一轮评价已完成时,先清空上一轮进度再开新局
            if state.get("need_reset"):
                print("开启新一轮,重置上一轮进度")
                return Command(goto="reset")
            return Command(goto="question")
        #首次出题(old_total=0)也走 question
        if not (state.get("questions") or []):
            return Command(goto="question")
        #答题轮:意图已判定为答题,进入收答案
        print("判定为答题,收集答案")
        return Command(goto="answer")
    elif exam_state == "question":
        #题目已下发,等待用户。这一轮如果是用户发言,必须先判定"答题"还是"要新题"。
        #原来的代码只要"是用户发言"就一律当答案,导致用户说"再来一道"时,
        #那句请求被当成答案送去评价,会话直接被终结,新题永远出不来。
        if not is_user_turn:
            print("等待用户输入答案")
            return Command(goto=END)
        print("先判定用户本轮意图")
        return Command(goto="intent")

    elif exam_state == "answer":
        if continue_question:
            print("继续出题")
            return Command(goto="question")
        else:
            print("答案结束")
            return Command(goto="evaluate")
    elif exam_state == "evaluate":
        #evaluate 节点执行中/已完成,不能再跳回自己,否则死循环
        return Command(goto=END)
    elif exam_state == "done": #评价结束
        #评价已出。如果用户当初要了多道题(remaining>0),这里应自动接着出下一题,
        #不必让用户再说一次"再来一道"。
        if state.get("remaining",0) > 0 and not is_user_turn:
            print(f"还有{state.get('remaining')}道题未出,继续出题")
            return Command(goto="question")
        #用户继续说话时先判定意图,决定是开新一轮还是忽略
        if not is_user_turn:
            return Command(goto=END)
        print("评价结束后用户继续发言,先判定意图")
        return Command(goto="intent")
    elif exam_state == "reset":
        #新一轮已就绪(进度已清空),进入出题
        return Command(goto="question")
    else:
        return Command(goto=END)
