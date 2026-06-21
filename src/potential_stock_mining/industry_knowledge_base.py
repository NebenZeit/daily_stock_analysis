"""
产业知识库管理

加载 YAML 配置的赛道定义，提供关键词匹配和赛道信息查询。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

DEFAULT_KB_PATH = "config/industry_kb.yaml"


class IndustryKnowledgeBase:
    """产业知识库"""

    def __init__(self, path: Optional[str] = None):
        self._path = Path(path or DEFAULT_KB_PATH)
        self._sectors: dict[str, dict] = {}
        self._load()

    def _load(self):
        if not self._path.exists():
            logger.warning("Industry KB not found: %s", self._path)
            return
        try:
            data = yaml.safe_load(self._path.read_text(encoding="utf-8"))
            self._sectors = data.get("sectors", {}) if isinstance(data, dict) else {}
            logger.info("Loaded %d sectors from %s", len(self._sectors), self._path)
        except Exception as e:
            logger.error("Failed to load industry KB: %s", e)

    def reload(self):
        self._load()

    def list_sectors(self) -> list[dict]:
        """列出所有赛道"""
        return [
            {
                "sector_id": sid,
                "sector_name": info.get("sector_name", sid),
                "description": info.get("description", ""),
                "keywords": info.get("keywords", []),
                "products": info.get("products", []),
                "related_industries": info.get("related_industries", []),
                "company_count": len(info.get("company_mappings", [])),
            }
            for sid, info in self._sectors.items()
        ]

    def get_sector(self, sector_id: str) -> Optional[dict]:
        return self._sectors.get(sector_id)

    def match_announcement(self, title: str, sector_id: str) -> bool:
        """判断一条公告标题是否匹配指定赛道的关键词"""
        sector = self._sectors.get(sector_id)
        if not sector:
            return False
        keywords = sector.get("keywords", [])
        products = sector.get("products", [])
        all_terms = keywords + products
        return any(term in title for term in all_terms)

    def match_any_sector(self, title: str) -> list[str]:
        """返回匹配给定标题的所有赛道 ID"""
        matched = []
        for sid in self._sectors:
            if self.match_announcement(title, sid):
                matched.append(sid)
        return matched
