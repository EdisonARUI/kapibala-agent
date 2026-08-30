from typing import TypedDict, Annotated, List
import operator
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    intent: str
    is_unhappy: bool
    abnormal_count: int
    is_escalated: bool
    message_timestamps: List[float]
    reply_content: str
