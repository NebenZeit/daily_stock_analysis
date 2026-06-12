# -*- coding: utf-8 -*-
"""轻量消息模型（原 bot.models，供 pipeline / 通知 / 任务队列复用）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ChatType(str, Enum):
    """会话类型"""

    GROUP = "group"
    PRIVATE = "private"
    UNKNOWN = "unknown"


@dataclass
class BotMessage:
    """统一的消息上下文（用于通知回传到来源会话，Web/CLI 通常为空）。"""

    platform: str
    message_id: str
    user_id: str
    user_name: str
    chat_id: str
    chat_type: ChatType
    content: str
    raw_content: str = ""
    mentioned: bool = False
    mentions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    raw_data: Dict[str, Any] = field(default_factory=dict)
