# 解析模块 (Parsing Module) - 技术文档

## 概述

解析模块 (Parsing Module) 起到桥梁的作用，它包含两个核心节点（`parser_node` 和 `reply_parser_node`）。分别负责：
1. **前置意图校验**：将意图识别模块输出的非结构化/半结构化对象转化为系统可识别的、强类型的对象，防御 LLM 幻觉。
2. **后置回复清洗**：将动作执行模块输出的最终回复进行格式清洗和防泄漏校验，确保发给用户的文本安全、干净。

---

## 1. 架构概览

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                            解析模块 (Parsing)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [前置意图校验 parser_node]                                                   │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                      │
│  │   状态传入   │───▶│  Pydantic   │───▶│ 异常与兜底  │                      │
│  │  (intent等)  │    │  Schema校验 │    │  (Fallback) │                      │
│  └─────────────┘    └──────┬──────┘    └─────────────┘                      │
│                            │                                                │
│                      (严格校验枚举)                                           │
│                                                                             │
│  [后置回复清洗 reply_parser_node]                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                      │
│  │  生成的回复  │───▶│ 正则前缀清洗│───▶│  动作安全性  │                      │
│  │ (reply_node)│    │(防套话/格式) │    │  (校验Action)│                      │
│  └─────────────┘    └─────────────┘    └─────────────┘                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 核心功能

### 2.1 强类型前置校验 (`parser_node`)
- 定义 `Pydantic BaseModel`，要求包含精确的字段：
  - `intent`: `Literal["interested", "needs_info", "rejected", "irrelevant", "escalate_to_human", "other"]`
  - `is_unhappy`: 严格的 `bool` 类型。
- **兜底策略 (Fallback)**：如果传入的状态被污染或大模型幻觉输出了不合法的意图，解析模块将其强制拦截并降级为 `irrelevant`。

### 2.2 后置回复清洗 (`reply_parser_node`)
- **格式与前缀过滤**：大模型在使用 Few-Shot 时，偶尔会将提示词里的标签（如 `"Assistant: "`）带入到最终输出中。此节点使用正则拦截并移除此类冗余字符。
- **防泄漏保护**：移除生成过程中的内部思维标签（如 `<think>...</think>`）。
- **执行动作校验**：校验路由传来的 `action` 字段，确保只能是预定义的动作之一，防止系统异常状态流转。

---

## 3. 数据流转与实现机制

```python
import re
from pydantic import BaseModel, Field, ValidationError
from typing import Literal

class ParsedIntent(BaseModel):
    intent: Literal["interested", "needs_info", "rejected", "irrelevant", "escalate_to_human", "other"]
    is_unhappy: bool = Field(default=False)

def parser_node(state: dict) -> dict:
    try:
        # Pydantic 自动解析与校验
        parsed = ParsedIntent(intent=state.get("intent"), is_unhappy=state.get("is_unhappy", False))
        return {"intent": parsed.intent, "is_unhappy": parsed.is_unhappy}
    except ValidationError:
        return {"intent": "irrelevant"}

def reply_parser_node(state: dict) -> dict:
    reply_content = state.get("reply_content", "")
    if reply_content:
        reply_content = re.sub(r"^(Assistant|AI|客服)[:：\s]*", "", reply_content, flags=re.IGNORECASE)
        reply_content = re.sub(r"<think>.*?</think>", "", reply_content, flags=re.DOTALL)
    
    # 动作合法性校验兜底
    action = state.get("action", "reply")
    if action not in ["reply", "schedule_followup", "escalate_to_human", "mark_not_interested"]:
        action = "reply"
        
    return {"reply_content": reply_content.strip(), "action": action}
```

---

[← 返回架构文档](ARCHITECTURE.md)
