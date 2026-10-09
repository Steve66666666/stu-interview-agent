from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel,Field

from app.ai.agent.multi_agent.state.exam_state import ExamState
from app.ai.model.my_model import MyModel
from langchain.agents import create_agent

from app.ai.prompt.builder_prompt import BuilderPromptYaml

"""
意图识别节点。承担两件事:
  1) 首次出题:解析课程与题目数量
  2) 答题途中用户发言:判定用户是在"答题"还是在"追加题目"
判定结果写入 user_action,由 manager 决定下一跳。
"""

#课程名归一化表:库中 question_subject 存的是 Python/Java/前端/数据库,
#模型可能输出小写,不归一化会一道题都查不到
_COURSE_MAP = {
    "python": "Python",
    "java": "Java",
    "前端": "前端",
    "数据库": "数据库",
}


class IntentSchema(BaseModel):
    action:str = Field(
        ...,
        description="用户意图,只能填 answer 或 add。answer=用户正在回答当前面试题; add=用户要求再出新的题目"
    )
    course:str = Field(...,description="课程名称")
    num:int = Field(...,description="本次要出题的数量;非出题意图时填 1")


prompt = BuilderPromptYaml.get_prompt("intent_node.yaml")


def _last_user_input(state:ExamState) -> str:
    """取最后一条用户消息,避免多轮时永远读到开场那句"""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            return msg.content
    return ""


def intent_node(state:ExamState):
    user_input = _last_user_input(state)

    #获取当前进度,用于判断这是首次出题、答题途中追加,还是评价后开新一轮
    questions = state.get("questions") or []
    current = state.get("current",0)
    old_total = state.get("total",0)
    has_question = len(questions) > 0
    #上一轮评价已经出过了。此时用户再要题,属于开启全新一轮,
    #不能把新题累加到上一轮已经评价完的进度上。
    finished = state.get("exam_step") == "done"

    #结构化输出用在线模型:本地小模型(qwen2.5:3b)的 JSON 能力不足以稳定返回结构化结果
    model = MyModel.get_model()
    agent = create_agent(
        model=model,
        system_prompt=prompt,
        response_format=IntentSchema
    )
    rs = agent.invoke({"messages":[HumanMessage(content=user_input)]})
    data = rs["structured_response"].model_dump()

    #只认 add,其余一律按 answer 处理。默认 answer 是安全侧:
    #最坏是把"要新题"误判成"答题"(用户可再说一次),而不是把用户答案直接丢掉。
    action = "add" if str(data.get("action","")).strip().lower() == "add" else "answer"

    #课程兜底并归一化:用户追加题目时往往不重复说课程,沿用上下文
    course = str(data.get("course") or "").strip()
    if not course:
        course = state.get("course") or "Python"
    course = _COURSE_MAP.get(course.lower(), course)

    num = data.get("num",1)
    if not isinstance(num,int) or num < 1:
        num = 1

    reset = False
    #剩余待出题数:出题节点每出一题减一
    remaining = state.get("remaining",0)
    if not has_question:
        #首次出题
        total = num
        remaining = num
        ai_msg = f"\n意图识别成功，课程名称{course},课程数量{total}\n"
    elif finished and action == "add":
        #评价后重新要题:开新一轮,进度归零
        total = num
        remaining = num
        reset = True
        ai_msg = f"\n开始新一轮面试，课程名称{course},课程数量{total}\n"
    elif action == "add":
        #答题途中追加:在原进度上累加,已出题目与已收集的答案都不作废
        base = max(old_total,current)
        total = base + num
        remaining = remaining + num
        ai_msg = f"\n收到，在原有{base}道题的基础上再追加{num}道，共{total}道。课程：{course}\n"
    else:
        #用户在答题,题量不变
        total = old_total if old_total else num
        ai_msg = ""

    result = {
        "course":course,
        "total":total,
        "remaining":remaining,
        #把意图传下去,manager 靠它分流
        "user_action":action,
        #true 表示这是评价之后的新一轮,manager 需要先重置上一轮进度
        "need_reset":reset,
        #回写状态,manager 靠它决定下一跳
        "exam_step":"intent"
    }
    #只在真正有提示语时才追加消息,避免答题轮插入无意义的空消息
    if ai_msg:
        result["messages"] = [AIMessage(content=ai_msg)]
    return result
