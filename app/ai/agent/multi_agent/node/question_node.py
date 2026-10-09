import ast

from langchain_core.messages import AIMessage

from app.ai.agent.multi_agent.state.exam_state import ExamState
from app.ai.tool.mysql_tool import mysql_tool


def question_node(state:ExamState):
    course = state['course']
    question_list = list(state.get('questions') or [])
    #标准答案单独存放,只用于评分,不放进 questions 以免泄漏给前端
    sure_answer = list(state.get('sure_answer') or [])
    current = state.get('current',0)+1
    #剩余待出题数。由于每题答完立即评价,一次只应有一道题处于"待作答"状态,
    #用 remaining 记录用户还要几道题,每出一题减一。
    remaining = state.get('remaining',0)

    #按课程筛选(question_subject 实际存的是 Java/Python/前端/数据库),排除已出过的题目,随机取一道
    #用 lower() 做不区分大小写匹配:意图识别可能给出 python/java 这类小写,
    #而库里存的是 Python/Java,直接等值比较会一道题都查不到
    course_key = str(course).strip().lower()
    if len(question_list) > 0:
        used = ",".join([str(i["id"]) for i in question_list])
        sql = (f"select * from question_bank where lower(question_subject)=lower('{course_key}') "
               f"and question_id not in ({used}) ORDER BY RAND() LIMIT 1")
    else:
        sql = (f"select * from question_bank where lower(question_subject)=lower('{course_key}') "
               f"ORDER BY RAND() LIMIT 1")
    #调用mysql工具
    rs = mysql_tool.invoke({"sql": sql})
    data = ast.literal_eval(rs)
    #查询结果为空,说明该课程题库已抽完或课程名对不上
    if not data:
        return {
            "messages":[AIMessage(content=f"\n题库中没有找到课程「{course}」的题目，请确认课程名称（支持 Python、Java、前端、数据库）\n")],
            "exam_step":"done",
            "continue_question":False
        }
    row = data[0]
    #真实字段顺序:question_id, question_title, answer, question_type, question_subject
    question_id = row[0]
    question_name = row[1]
    question_answer = row[2]
    question_list.append({"id":question_id,"question":question_name})
    sure_answer.append({"id":question_id,"answer":question_answer})
    #ai回复消息
    ai_msg = f"\n第{current}题：{question_name}\n"
    return {
        #键名必须是 messages,写成 message 状态不会被LangGraph合并,前端收不到题目
        "messages":[AIMessage(content=ai_msg)],
        "questions":question_list,
        "sure_answer":sure_answer,
        "current":current,
        #当前题目编号,answer_node 记录用户答案时要用
        "question_id":question_id,
        "current_question":question_name,
        #本題已下发,剩余待出题数减一
        "remaining":max(remaining-1,0),
        #回写状态,manager 下一步才会走 answer 分支
        "exam_step":"question"
    }
