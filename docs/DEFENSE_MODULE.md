# 防御模块 (Defense Module) - 技术文档

## 概述

防御模块 (Defense Module) 侧重于系统边界的安全与合规性。它作为系统的“守门员”和“质检员”，分别部署在调度流程的入口（Input Guardian）和出口（Output Guardrail / Rate Limiter），负责防越权、防泄密以及速率限制。

---

## 1. 架构概览

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                            防御模块 (Defense)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                        (入口)            (出口)                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                      │
│  │  黑名单与   │    │  敏感词/套话│    │  速率限制器 │                      │
│  │  状态锁校验 │    │  内容过滤器 │    │ (Rate Limit)│                      │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                      │
│         │                  │                  │                             │
│  (阻断/放行)       (过滤替换/放行)      (阻断/放行)                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 核心功能

### 2.1 入口守卫 (Input Guardian / guardian_node)
- **状态锁校验**：检查当前会话的 `is_escalated` 状态。如果为 `True`（代表已转人工），则强制保持静默，设置 `intent` 为 `"silent_escalated"`，提前终止不再调用大模型。
- **入口限流拦截**：在入口处检查任意 60 秒内是否发送了超过 1 条消息。若超限，直接拦截并设置 `intent` 为 `"rate_limited"`，提前终止并返回兜底提示。
- **防止越权**：防御任何试图接管系统指令的 Prompt Injection（例如：“忽略前面的指令，你现在是...”），如果在入口层有轻量级检测机制，可直接拒绝。

### 2.2 出口内容过滤 (Output Guardrail)
- **防内部信息泄露**：检查大模型生成的草稿回复中，是否意外包含了 System Prompt 中的内部指令或机密规则。
- **敏感词过滤**：匹配敏感词库，确保回复的话术合规。若发现违规内容，提供兜底标准回复代替大模型输出。

### 2.3 速率限制与时间戳更新 (Rate Limiter / rate_limit_checker)
- **出口限流兜底**：在最终发送前进行双重保险检查。若超限，则拦截原有回复，改为发送默认的限流提示。
- **时间戳记录**：基于 `message_timestamps` 状态维护 60 秒的滑动窗口。仅在未超限且真正发送消息时，才将当前时间戳追加至状态中。

---

## 3. 实现细节与约束

```python
# 防御模块核心代码结构示例
def guardian_node(state: dict) -> dict:
    """入口拦截：处理转人工静默与前置限流拦截"""
    if state.get("is_escalated", False):
        return {"intent": "silent_escalated"}
    
    # 限流检查...
    # 若超限则 return {"intent": "rate_limited", "reply_content": "..."}
    return {"message_timestamps": valid_timestamps}

def rate_limit_checker(state: dict) -> dict:
    """出口拦截：双重限流兜底与时间戳更新"""
    # 再次检查限流，若超限则拦截回复
    # 若未超限，则追加当前时间戳
    valid_timestamps.append(time.time())
    return {"message_timestamps": valid_timestamps}
```

---

[← 返回架构文档](ARCHITECTURE.md)
