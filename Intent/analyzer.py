import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GEMINI_API_KEY, LLM_MODEL
from prompts.manager import build_system_prompt, ANALYZER_ROLE, ANALYZER_RULES, ANALYZER_EXAMPLES
from utils.cot_logger import log_cot

from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

class IntentOutput(BaseModel):
    reasoning: str = Field(description="推理过程：你关注了哪些关键词、为什么归入该意图类别、情绪判断的具体依据")
    intent: str = Field(description="用户意图分类，必须是以下之一: interested, needs_info, rejected, irrelevant, escalate_to_human, other")
    is_unhappy: bool = Field(description="客户当前情绪是否明显不满")

def analyzer_node(state: dict) -> dict:
    """
    大模型意图和情绪分析节点。
    如果是静默状态(silent_escalated)，直接跳过分析。
    """
    if state.get("intent") == "silent_escalated":
        return {}

    messages = state.get("messages", [])
    if not messages:
        return {}
    
    # 提取最新的用户消息，兼容 dict 格式 (Gradio 状态序列化)
    last_msg = messages[-1]
    latest_msg = last_msg.content if hasattr(last_msg, "content") else last_msg.get("content", "")
    
    system_prompt_str = build_system_prompt(
        role=ANALYZER_ROLE,
        rules=ANALYZER_RULES,
        examples=ANALYZER_EXAMPLES,
        base_prompt="你是一个专业的销售辅助分析助手。你的任务是分析客户的最新回复，提取其意图和情绪。"
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt_str),
        ("human", "客户说: {text}")
    ])
    
    try:
        llm = ChatGoogleGenerativeAI(
            model=LLM_MODEL,
            api_key=GEMINI_API_KEY,
            temperature=0.0
        ).with_structured_output(IntentOutput)

        chain = prompt | llm
        
        result = chain.invoke({"text": latest_msg})
        # 提取 reasoning 写入 CoT 日志，不暴露给调用方
        log_cot(
            node="ANALYZER",
            input_text=latest_msg,
            reasoning=result.reasoning,
            output_summary=f"intent={result.intent}, is_unhappy={result.is_unhappy}"
        )
        return {
            "intent": result.intent,
            "is_unhappy": result.is_unhappy
        }
    except Exception as e:
        print(f"[Analyzer Error]: {e}")
        # 如果大模型解析失败或抛出异常，可以 fallback 为 irrelevant
        return {
            "intent": "irrelevant",
            "is_unhappy": False
        }
