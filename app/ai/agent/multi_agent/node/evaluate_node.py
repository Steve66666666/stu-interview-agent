from langchain_core.messages import HumanMessage, AIMessage
from app.ai.model.my_model import MyModel
from app.ai.agent.multi_agent.state.exam_state import ExamState
from app.ai.prompt.builder_prompt import  BuilderPromptYaml
from langchain.agents import create_agent
from langgraph.config import get_stream_writer

"""
评价节点
"""
#读取外部配置文件
prompt = BuilderPromptYaml.get_prompt("evaluate_node.yaml")
async def evaluate_node(state:ExamState):
    #每题答完立即评价,所以这里只针对"刚答完的那一题"评分,
    #不再把历史所有题目重新评一遍,避免报告越滚越长且重复计分。
    current_qid = state.get("question_id")
    current_qname = state.get("current_question","")
    #定位刚作答的那一条答案(取最后一条,即本轮新增的)
    user_answer_list = state.get("user_answer_list") or []
    latest_answer = user_answer_list[-1] if user_answer_list else {}
    answer_text = latest_answer.get("answer","")
    #找出对应的标准答案。evaluate_node.yaml 要求按"问题+用户答案+正确答案"评分,
    #漏传正确答案模型只能凭自己编,评分没有依据
    sure_answer = state.get("sure_answer") or []
    correct = ""
    for item in sure_answer:
        if item.get("id") == current_qid:
            correct = item.get("answer","")
            break
    #构建提问内容:只包含本轮这一题
    question = (f"问题列表:[{{'id':{current_qid},'question':{current_qname!r}}}]\n"
                f"用户答案列表:[{{'id':{current_qid},'answer':{answer_text!r}}}]\n"
                f"正确答案列表:[{{'id':{current_qid},'answer':{correct!r}}}]")
    #调用模型
    model = MyModel.get_model()
    #提示词
    agent = create_agent(
        model =model,
        system_prompt=prompt,
    )
    #提问
    user_msg ={"messages":[HumanMessage(content=question)]}
    #异步流式
    result =[]
    #获取流式写入对象
    write = get_stream_writer()
    async for c,m in agent.astream(user_msg,stream_mode="messages"):
        if c.content:
            result.append(c.content)
            write(c.content)

    #把流式片段拼回完整文本,存入 evaluation 字段持久化,便于后续回溯
    evaluation = "".join(result)
    #把本轮评价追加到历史评价里,保留每题的评价记录
    history = state.get("evaluation") or ""
    merged = (history + "\n\n---\n\n" + evaluation).strip() if history else evaluation
    return {
        #这里必须返回空内容的 AIMessage,不能把评价文本再放进来。
        #原因:评价文本已经通过上面的 write() 走 custom 通道实时推送过了,
        #而 ExamGraph.chat() 同时订阅了 messages 和 custom 两个流,
        #若这里再带非空 content,yield 会执行两次,前端就会看到两份重复的评价。
        "messages":[AIMessage(content="")],
        #评价全文单独存字段:既保证可回溯,又不会和 custom 通道重复输出
        "evaluation":merged,
        #评价完成。用户再说"再来一道"时 manager 会开启新一轮出题。
        "exam_step":"done"
    }
