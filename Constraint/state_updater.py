def state_updater_node(state: dict) -> dict:
    """
    业务约束状态机更新节点：
    根据解析出的意图和情绪，更新异常计数器。
    如果连续异常 >= 2 次，则强制转人工 (is_escalated = True)，覆写意图。
    """
    intent = state.get("intent")
    is_unhappy = state.get("is_unhappy", False)
    
    if intent == "silent_escalated":
        return {}
        
    current_count = state.get("abnormal_count", 0)
    
    # 判定为"答非所问"或"情绪不满"，增加异常计数
    if intent == "irrelevant" or is_unhappy:
        current_count += 1
    else:
        current_count = 0  # 恢复正常沟通，清零
        
    new_intent = intent
    is_escalated = state.get("is_escalated", False)
    
    # 强制业务约束规则
    if current_count >= 2:
        is_escalated = True
        new_intent = "escalate_to_human"
        
    # 主动转人工也需要将 is_escalated 状态置为 True
    if new_intent == "escalate_to_human":
        is_escalated = True
        
    return {
        "abnormal_count": current_count,
        "is_escalated": is_escalated,
        "intent": new_intent
    }

def reset_escalation_state() -> dict:
    """
    提供给外部独立调用的 API，用于完全脱离对话流程重置静默状态。
    可以在主程序/CLI中，通过特定命令重新初始化 State。
    """
    return {
        "is_escalated": False,
        "abnormal_count": 0,
        "intent": ""
    }
