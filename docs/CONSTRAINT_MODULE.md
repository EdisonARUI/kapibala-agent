# 约束模块 (Constraint Module) - 技术文档

## 概述

约束模块 (Constraint Module) 侧重于核心业务逻辑的管控。它不依赖大模型，而是通过纯代码逻辑（Hard-coded logic）维护状态机。它的核心职责是基于解析出的意图，修改系统的内部计数器，并决定是否触发如“强制转人工”等业务流程干预。

---

## 1. 架构概览

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                            约束模块 (Constraint)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                      │
│  │ 状态变更规则│───▶│ 阈值判断器  │───▶│ 意图覆写器  │                      │
│  │ (State Rules)    │ (Threshold) │    │ (Override)  │                      │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                      │
│         │                  │                  │                             │
│   (如:异常计数+1)     (如:连续>=2次)    (覆写意图为转人工)                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 核心功能

### 2.1 状态维护 (State Updater)
- 读取当前状态字典（`AgentState`）中的 `abnormal_count`。
- 如果解析模块传来的 `intent` 是“答非所问”，或者 `sentiment_is_unhappy` 是 `True`，则将 `abnormal_count` 自增 1。
- 如果属于正常沟通，则将其重置为 0。

### 2.2 流程干预与意图覆写
- 校验业务规则阈值。一旦 `abnormal_count >= 2`：
  - 触发状态锁：将状态机的 `is_escalated` 置为 `True`，确保该状态持久化。
  - **覆写意图**：无视大模型原本解析出的意图，直接将传递给下游的 `intent` 强制修改为 `"escalate_to_human"`。

---

## 3. 实现细节

此模块体现了人机协作系统中“机器失控”时的最终保障：

```python
def constraint_node(state: AgentState, parsed_intent: str, is_unhappy: bool):
    current_count = state.get("abnormal_count", 0)
    
    if parsed_intent == "答非所问" or is_unhappy:
        current_count += 1
    else:
        current_count = 0  # 恢复正常，重置
        
    new_intent = parsed_intent
    is_escalated = state.get("is_escalated", False)
    
    # 强制业务约束规则
    if current_count >= 2:
        is_escalated = True
        new_intent = "escalate_to_human"
        
    return {
        "abnormal_count": current_count,
        "is_escalated": is_escalated,
        "intent": new_intent
    }
```

---

[← 返回架构文档](ARCHITECTURE.md)
