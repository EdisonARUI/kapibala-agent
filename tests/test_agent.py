import os
import pytest
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from graph.workflow import create_workflow

@pytest.fixture(scope="module")
def app():
    load_dotenv("env.local")
    return create_workflow()

def test_escalation_state_machine(app):
    """
    测试连续两次异常意图（答非所问/情绪不满）导致强制转人工。
    为避免真实调用大模型产生费用并保证测试确定性，
    我们可以通过直接提供构造好的 intent 给状态机，
    或者利用依赖注入/mock。
    但 LangGraph 可以直接让我们从特定的状态开始跑！
    """
    # 模拟 Analyzer 输出了 irrelevant 和 unhappy
    initial_state = {
        "messages": [HumanMessage(content="你是谁")],
        "intent": "irrelevant",
        "is_unhappy": True,
        "abnormal_count": 0,
        "is_escalated": False,
        "message_timestamps": [],
        "reply_content": ""
    }
    
    # 我们仅调用 state_updater_node 来测纯函数逻辑更稳妥
    from Constraint.state_updater import state_updater_node
    
    # 第一次异常
    res1 = state_updater_node(initial_state)
    assert res1["abnormal_count"] == 1
    assert res1["is_escalated"] == False
    
    # 第二次异常
    initial_state["abnormal_count"] = 1
    res2 = state_updater_node(initial_state)
    assert res2["abnormal_count"] == 2
    assert res2["is_escalated"] == True
    assert res2["intent"] == "escalate_to_human"

def test_rate_limiter():
    """测试速率限制滑动窗口逻辑"""
    from Defense.guardian import rate_limit_checker
    import time
    
    # 假设最近 10 秒内发过一条
    state = {
        "message_timestamps": [time.time() - 10]
    }
    
    res = rate_limit_checker(state)
    # 因为 60秒内有一条，所以触发限速，返回默认提示
    assert "reply_content" in res
    assert res["reply_content"] == "您发送消息过于频繁，请稍后再试。"
    
    # 假设 70 秒前发过一条（过期了）
    state2 = {
        "message_timestamps": [time.time() - 70]
    }
    res2 = rate_limit_checker(state2)
    # 不应该有限速提示
    assert "reply_content" not in res2
    assert len(res2["message_timestamps"]) == 1 # 自动追加当前时间戳

def test_guardian_node():
    """测试入口静默状态检查"""
    from Defense.guardian import guardian_node
    
    state = {"is_escalated": True}
    res = guardian_node(state)
    assert res["intent"] == "silent_escalated"
    
    state2 = {"is_escalated": False}
    res2 = guardian_node(state2)
    assert res2.get("intent") != "silent_escalated"
