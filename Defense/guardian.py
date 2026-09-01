import time
from typing import Dict, Any

def guardian_node(state: dict) -> dict:
    """
    入口拦截检查：
    1. 检查是否已经处于转人工静默状态 (is_escalated)。
       如果是，强制阻断并提前终止。
    2. 检查在任意 60 秒内是否发送了超过 1 条主动消息。
       如果是，直接在入口拦截，提前终止，不调用大模型。
    """
    is_escalated = state.get("is_escalated", False)
    if is_escalated:
        # 如果已经转人工，忽略用户的任何输入，保持静默。
        # 我们可以在状态里打个标记或者直接设定 intent 为 "escalate_to_human" 
        # 来走特定的跳过逻辑。但最安全的是直接修改意图为 "SILENT" 或保持转人工状态。
        return {"intent": "silent_escalated"}
    
    timestamps = state.get("message_timestamps", [])
    now = time.time()
    
    # 清理 60 秒以外的时间戳
    valid_timestamps = [ts for ts in timestamps if now - ts < 60]
    
    if len(valid_timestamps) >= 1:
        # 触发限流，直接在入口拦截，设置限流意图和回复内容
        return {
            "intent": "rate_limited",
            "reply_content": "您发送消息过于频繁，请稍后再试。",
            "message_timestamps": valid_timestamps
        }
    
    return {"message_timestamps": valid_timestamps}

def rate_limit_checker(state: dict) -> dict:
    """
    出口拦截与记录时间戳：
    1. 再次确认时间戳是否超出限制（做最后的双重保险兜底）。
    2. 如果超出，则拦截原有回复，改为发送默认提示。
    3. 若未超限，在此处真正记录当前发送的时间戳。
    """
    timestamps = state.get("message_timestamps", [])
    now = time.time()
    
    # 清理 60 秒以外的时间戳
    valid_timestamps = [ts for ts in timestamps if now - ts < 60]
    
    if len(valid_timestamps) >= 1:
        # 触发限流，向用户返回默认提示
        return {
            "reply_content": "您发送消息过于频繁，请稍后再试。",
            "message_timestamps": valid_timestamps
        }
    
    # 记录当前发送的时间戳
    valid_timestamps.append(now)
    return {"message_timestamps": valid_timestamps}
