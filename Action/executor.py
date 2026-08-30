import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GEMINI_API_KEY, LLM_MODEL
from Prompts.manager import build_system_prompt, EXECUTOR_ROLE, EXECUTOR_RULES, EXECUTOR_EXAMPLES

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage

def reply_node(state: dict) -> dict:
    """执行 reply 动作：调用大模型生成回复。"""
    messages = state.get("messages", [])
    if not messages:
        return {}
        
    llm = ChatGoogleGenerativeAI(
        model=LLM_MODEL,
        api_key=GEMINI_API_KEY,
        temperature=0.7
    )
    
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
    
    chain = prompt | llm
    
    try:
        response = chain.invoke({"messages": messages})
        return {"reply_content": response.content}
    except Exception as e:
        return {"reply_content": "抱歉，我暂时无法回答这个问题。"}

def schedule_followup_node(state: dict) -> dict:
    """执行 schedule_followup 动作"""
    return {"reply_content": "[系统动作]: 已为您标记稍后跟进，本轮不回复。"}

def escalate_to_human_node(state: dict) -> dict:
    """执行 escalate_to_human 动作"""
    return {"reply_content": "[系统动作]: 已为您转接人工客服。系统进入静默状态。"}

def mark_not_interested_node(state: dict) -> dict:
    """执行 mark_not_interested 动作"""
    return {"reply_content": "[系统动作]: 客户不感兴趣，已结束当前会话。"}
