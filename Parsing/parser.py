def parser_node(state: dict) -> dict:
    """
    解析模块：
    虽然 analyzer 已经使用了 structured_output，但这里依然做一次强制的安全映射和校验，
    以防止幻觉导致输出不在我们的合法意图列表中。
    """
    intent = state.get("intent")
    
    if intent == "silent_escalated":
        return {}
        
    valid_intents = ["interested", "needs_info", "rejected", "irrelevant", "other"]
    
    if intent not in valid_intents:
        # 兜底：如果模型输出了不合法的意图，强制设为 irrelevant
        return {"intent": "irrelevant"}
        
    return {}
