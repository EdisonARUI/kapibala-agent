import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GEMINI_API_KEY, LLM_MODEL
from prompts.manager import build_system_prompt, EXECUTOR_ROLE, EXECUTOR_RULES, EXECUTOR_EXAMPLES
from utils.cot_logger import log_cot

from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage

class ExecutorOutput(BaseModel):
    reasoning: str = Field(description="生成回复前的思考过程：客户的核心诉求、回复策略选择理由、是否需要引导到下一步")
    reply: str = Field(description="最终给客户的回复内容，简短友好")

def reply_node(state: dict) -> dict:
    """执行 reply 动作：调用大模型生成回复。"""
    messages = state.get("messages", [])
    if not messages:
        return {}

    # 动态组装生成回复的 Prompt
    system_prompt_str = build_system_prompt(
        role=EXECUTOR_ROLE,
        rules=EXECUTOR_RULES,
        examples=EXECUTOR_EXAMPLES,
        base_prompt="你是一个专业的销售辅助客服。请根据客户的最新问题生成简短、友好的回复。"
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt_str),
        ("placeholder", "{messages}")
    ])

    try:
        llm = ChatGoogleGenerativeAI(
            model=LLM_MODEL,
            api_key=GEMINI_API_KEY,
            temperature=0.7
        ).with_structured_output(ExecutorOutput)

        chain = prompt | llm
        
        result = chain.invoke({"messages": messages})
        # 提取最近一条用户消息作为输入摘要
        latest_input = messages[-1].content if messages else ""
        log_cot(
            node="EXECUTOR",
            input_text=latest_input,
            reasoning=result.reasoning,
            output_summary=result.reply[:100]  # 只记录回复前 100 个字符
        )
        return {"reply_content": result.reply, "action": "reply"}
    except Exception as e:
        return {"reply_content": "抱歉，我暂时无法回答这个问题。", "action": "reply"}

def schedule_followup_node(state: dict) -> dict:
    """执行 schedule_followup 动作"""
    return {"reply_content": "[系统动作]: 已为您标记稍后跟进，本轮不回复。", "action": "schedule_followup"}

def escalate_to_human_node(state: dict) -> dict:
    """执行 escalate_to_human 动作"""
    return {"reply_content": "[系统动作]: 已为您转接人工客服。系统进入静默状态。", "action": "escalate_to_human"}

def mark_not_interested_node(state: dict) -> dict:
    """执行 mark_not_interested 动作"""
    return {"reply_content": "[系统动作]: 客户不感兴趣，已结束当前会话。", "action": "mark_not_interested"}
