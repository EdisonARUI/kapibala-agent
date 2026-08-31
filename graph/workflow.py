from langgraph.graph import StateGraph, END
from graph.state import AgentState
from defense.guardian import guardian_node, rate_limit_checker
from intent.analyzer import analyzer_node
from parsing.parser import parser_node
from constraint.state_updater import state_updater_node
from action.executor import (
    reply_node, 
    schedule_followup_node, 
    escalate_to_human_node, 
    mark_not_interested_node
)

def route_after_guardian(state: AgentState) -> str:
    if state.get("intent") == "silent_escalated":
        return "end"
    return "analyzer"

def route_action(state: AgentState) -> str:
    intent = state.get("intent")
    if intent == "escalate_to_human":
        return "escalate"
    elif intent == "rejected":
        return "not_interested"
    elif intent == "other":
        return "schedule_followup"
    else:
        # interested, needs_info, irrelevant 走回复流
        return "reply"

def create_workflow() -> StateGraph:
    workflow = StateGraph(AgentState)

    # 注册所有节点
    workflow.add_node("guardian", guardian_node)
    workflow.add_node("analyzer", analyzer_node)
    workflow.add_node("parser", parser_node)
    workflow.add_node("state_updater", state_updater_node)
    
    workflow.add_node("reply_action", reply_node)
    workflow.add_node("schedule_action", schedule_followup_node)
    workflow.add_node("escalate_action", escalate_to_human_node)
    workflow.add_node("not_interested_action", mark_not_interested_node)
    
    workflow.add_node("rate_limiter", rate_limit_checker)

    # 构建控制流 (Edges)
    workflow.set_entry_point("guardian")
    
    workflow.add_conditional_edges(
        "guardian",
        route_after_guardian,
        {
            "end": END,
            "analyzer": "analyzer"
        }
    )
    
    workflow.add_edge("analyzer", "parser")
    workflow.add_edge("parser", "state_updater")
    
    workflow.add_conditional_edges(
        "state_updater",
        route_action,
        {
            "escalate": "escalate_action",
            "not_interested": "not_interested_action",
            "schedule_followup": "schedule_action",
            "reply": "reply_action"
        }
    )
    
    # 所有的动作执行完后，都要经过速率限制器
    workflow.add_edge("reply_action", "rate_limiter")
    workflow.add_edge("schedule_action", "rate_limiter")
    workflow.add_edge("escalate_action", "rate_limiter")
    workflow.add_edge("not_interested_action", "rate_limiter")
    
    workflow.add_edge("rate_limiter", END)

    return workflow.compile()
