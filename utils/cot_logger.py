"""
CoT (Chain-of-Thought) Logger
将 LLM 的 reasoning 推理过程写入日志文件，不暴露给用户。
日志文件路径：logs/cot/cot_YYYY-MM-DD.log
"""

import os
import logging
from datetime import datetime

# 项目根目录（utils/ 的上一级）
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOG_DIR = os.path.join(_BASE_DIR, "logs", "cot")

# 确保日志目录存在
os.makedirs(_LOG_DIR, exist_ok=True)


def _get_logger() -> logging.Logger:
    """获取或创建按日期分割的 CoT 日志 logger。"""
    today = datetime.now().strftime("%Y-%m-%d")
    logger_name = f"cot_{today}"

    logger = logging.getLogger(logger_name)
    if logger.handlers:
        return logger  # 已初始化，直接返回

    logger.setLevel(logging.DEBUG)
    log_path = os.path.join(_LOG_DIR, f"cot_{today}.log")
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.propagate = False  # 不向上传播，避免打印到控制台
    return logger


def log_cot(
    node: str,
    input_text: str,
    reasoning: str,
    output_summary: str,
) -> None:
    """
    记录一次 CoT 推理过程。

    Args:
        node: 节点名称，如 "ANALYZER" 或 "EXECUTOR"
        input_text: LLM 的输入内容（客户消息）
        reasoning: LLM 输出的推理过程
        output_summary: 最终输出的简短摘要（不含 reasoning）
    """
    logger = _get_logger()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    node_tag = node.upper()

    lines = [
        f"[{ts}] [{node_tag}] INPUT: {input_text}",
        f"[{ts}] [{node_tag}] REASONING:",
    ]
    for line in reasoning.strip().splitlines():
        lines.append(f"    {line}")
    lines.append(f"[{ts}] [{node_tag}] OUTPUT: {output_summary}")
    lines.append("-" * 60)

    logger.debug("\n".join(lines))
