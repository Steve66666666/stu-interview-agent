import operator
from typing import Annotated

from langchain_core.messages import AnyMessage
from typing_extensions import TypedDict


class ExamState(TypedDict):
    #AI消息列表
    messages: Annotated[list[AnyMessage],operator.add]
    #课程
    course:str
    #题目数量:用户累计要求的题数
    total:int
    #剩余待出题数:每出一题减一。因为每题答完立即评价,
    #靠它判断用户还要几道题,而不是靠比较已下发数与总数
    remaining:int
    #题库列表:仅存放前端展示需要的信息,不含正确答案
    questions:list[dict[str,any]]
    #标准答案列表:从题库取出的正确答案,只参与评分,不推送给前端
    sure_answer:list[dict[str,any]]
    #当前题目
    current_question:str
    #用户答案列表
    user_answer_list:list[dict[str,any]]
    #当前答题的题目索引
    current:int
    #评价结果
    evaluation:str
    #当前节点考试状态
    exam_step:str
    #当前题目编号
    question_id:int
    #是否继续出题
    continue_question:bool
    #本轮用户意图:start=首次出题 add=追加题目。manager 在 question 状态下靠它区分
    #"用户在答题" 还是 "用户想再要一道题"
    user_action:str
    #是否需要重置进度:评价结束后用户重新要题时为 True,需清空上一轮题目与答案
    need_reset:bool