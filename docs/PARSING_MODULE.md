# 解析模块 (Parsing Module) - 技术文档

## 概述

解析模块 (Parsing Module) 起到桥梁的作用，它负责将意图识别模块输出的非结构化/半结构化 JSON 字符串，转化为系统可识别的、强类型的对象。更重要的是，它负责处理 LLM 幻觉导致的格式错误，并提供重试与容错机制。

---

## 1. 架构概览

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                            解析模块 (Parsing)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                      │
│  │   JSON      │───▶│  Pydantic   │───▶│ 异常与重试  │                      │
│  │   解析器    │    │  Schema校验 │    │ 控制器      │                      │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                      │
│         │                  │                  │                             │
│   (处理转义异常)     (校验字段与枚举)   (触发重新生成)                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 核心功能

### 2.1 强类型校验
- 定义 `Pydantic BaseModel`，要求包含精确的字段：
  - `intent`: `Literal["reply", "schedule_followup", "escalate_to_human", "mark_not_interested", "答非所问"]`
  - `sentiment_is_unhappy`: `bool`

### 2.2 容错与重试机制 (Retry Controller)
- **JSON 语法错误**：若 LLM 未返回合法 JSON，解析模块捕获异常，将异常信息反馈给 LLM 并触发重试（最多重试 N 次）。
- **枚举越界错误**：若 LLM 返回的 `intent` 不在白名单枚举中，同样触发重试机制。
- **兜底策略 (Fallback)**：如果超过重试次数依然失败，解析模块提供默认安全值（如触发强制转人工或回复通用话术）。

---

## 3. 数据流转

```python
from pydantic import BaseModel, Field
from typing import Literal

class ParsedIntent(BaseModel):
    intent: Literal["reply", "schedule_followup", "escalate_to_human", "mark_not_interested", "答非所问"]
    sentiment_is_unhappy: bool = Field(default=False)

def parse_llm_output(raw_output: str) -> ParsedIntent:
    try:
        # Pydantic 自动解析与校验
        return ParsedIntent.parse_raw(raw_output)
    except ValidationError as e:
        # 触发重试逻辑...
        raise e
```

此模块输出的 `intent` 和 `sentiment_is_unhappy` 将作为下一环节（约束模块）的核心数据来源。

---

[← 返回架构文档](ARCHITECTURE.md)
