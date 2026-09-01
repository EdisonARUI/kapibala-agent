import re
from pydantic import BaseModel, Field, ValidationError
from typing import Literal

class ParsedIntent(BaseModel):
    intent: Literal["interested", "needs_info", "rejected", "irrelevant", "escalate_to_human", "other"]
    is_unhappy: bool = Field(default=False)

def parser_node(state: dict) -> dict:
    """
    解析模块：
    虽然 analyzer 已经使用了 structured_output，但这里依然做一次强制的安全映射和校验，
    以防止幻觉导致输出不在我们的合法意图列表中。
    """
    intent = state.get("intent")
    
    if intent == "silent_escalated":
        return {}
        
    try:
        # 使用 Pydantic 进行强类型校验和清洗
        parsed = ParsedIntent(
            intent=intent, 
            is_unhappy=state.get("is_unhappy", False)
        )
        return {"intent": parsed.intent, "is_unhappy": parsed.is_unhappy}
    except ValidationError:
        # 兜底：如果模型输出了不合法的意图或格式，强制设为 irrelevant
        return {"intent": "irrelevant"}

def reply_parser_node(state: dict) -> dict:
    """
    对大模型生成的最终回复进行清洗和格式化，防止暴露 Prompt 内容或包含废话前缀。
    """
    reply_content = state.get("reply_content", "")
    
    if reply_content:
        # 1. 移除可能产生的 Assistant 前缀
        reply_content = re.sub(r"^(Assistant|AI|客服)[:：\s]*", "", reply_content, flags=re.IGNORECASE)
        # 2. 移除可能的思维链标签，如 <think>...</think>
        reply_content = re.sub(r"<think>.*?</think>", "", reply_content, flags=re.DOTALL)
        # 3. 清理首尾空白
        reply_content = reply_content.strip()
    
    # 动作校验
    action = state.get("action", "reply")
    valid_actions = ["reply", "schedule_followup", "escalate_to_human", "mark_not_interested"]
    if action not in valid_actions:
        action = "reply"

    return {"reply_content": reply_content, "action": action}
