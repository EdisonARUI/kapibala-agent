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

### 2.1 入口守卫 (Input Guardian)
- **状态锁校验**：检查当前会话的 `is_escalated` 状态。如果为 `True`（代表已转人工），则必须**绝对阻断**当前用户的输入，不再调用任何 LLM 资源。
- **防止越权**：防御任何试图接管系统指令的 Prompt Injection（例如：“忽略前面的指令，你现在是...”），如果在入口层有轻量级检测机制，可直接拒绝。

### 2.2 出口内容过滤 (Output Guardrail)
- **防内部信息泄露**：检查大模型生成的草稿回复中，是否意外包含了 System Prompt 中的内部指令或机密规则。
- **敏感词过滤**：匹配敏感词库，确保回复的话术合规。若发现违规内容，提供兜底标准回复代替大模型输出。

### 2.3 速率限制 (Rate Limiter)
- 基于 `message_timestamps` 状态维护 60 秒的滑动窗口。
- 保证系统向单用户发送消息的频率不超过 1条/60s，防骚扰。超限则拦截发送行为。

---

## 3. 实现细节与约束

```python
# 速率限制伪代码示例
def rate_limiter_node(state: AgentState):
    now = current_timestamp()
    # 清理过期时间戳
    valid_timestamps = [t for t in state["message_timestamps"] if now - t < 60]
    
    if len(valid_timestamps) >= 1:
        raise RateLimitExceededException("60秒内仅能发送1条消息")
        
    valid_timestamps.append(now)
    return {"message_timestamps": valid_timestamps}
```

---

[← 返回架构文档](ARCHITECTURE.md)
