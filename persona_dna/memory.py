"""
Memory System - 记忆系统
========================
分层记忆存储 + 压缩机制 + 情绪联动检索。

三层架构:
- 即时层 (Immediate): soul/user/memory/tools/secret 等核心配置，每次对话自动加载
- 近中期层 (Recent): 索引+条目结构，存储项目进度、决策记录、待办等
- 长期层 (Long-term): 语义检索，基于向量数据库的历史对话记忆

五层渐进压缩:
1. 精确保留 (原话/原文)
2. 轻度摘要 (保留关键信息)
3. 中度压缩 (提取要点)
4. 高度概括 (一句话总结)
5. 标签归档 (仅保留标签+索引)
"""

import os
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Any, List, Dict
from dataclasses import dataclass, field, asdict
from enum import IntEnum


class MemoryLayer(IntEnum):
    """记忆层级。"""
    IMMEDIATE = 0    # 即时层：核心配置，每次加载
    RECENT = 1       # 近中期层：索引+条目
    LONG_TERM = 2    # 长期层：语义检索


class CompressionLevel(IntEnum):
    """压缩等级（五层渐进压缩）。"""
    VERBATIM = 1       # 精确保留
    LIGHT_SUMMARY = 2  # 轻度摘要
    MEDIUM = 3         # 中度压缩
    HIGH = 4           # 高度概括
    TAG_ONLY = 5       # 标签归档


@dataclass
class MemoryEntry:
    """单条记忆条目。"""
    id: str
    layer: int
    content: str
    tags: List[str] = field(default_factory=list)
    emotion: Optional[float] = None  # 情绪强度 -1.0 ~ 1.0
    created_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    compression_level: int = 1
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None
    weight: float = 1.0

    def touch(self):
        """标记一次访问。"""
        self.accessed_at = time.time()
        self.access_count += 1

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class MemorySystem:
    """
    分层记忆系统。

    即时层存储核心配置（soul/user/memory/tools/secret），
    近中期层使用索引+条目结构，
    长期层提供语义检索接口。
    """

    # 即时层预定义 key
    IMMEDIATE_KEYS = ["soul", "user", "memory", "tools", "secret"]

    def __init__(self, storage_path: str = "./memory_data"):
        self.storage_path = Path(storage_path)
        self._immediate: Dict[str, str] = {}
        self._recent_index: Dict[str, dict] = {}
        self._recent_entries: Dict[str, MemoryEntry] = {}
        self._long_term_store: List[MemoryEntry] = []

        self._init_storage()
        self._load_from_disk()

    # ─────────────────────────────────────────────
    # 即时层操作
    # ─────────────────────────────────────────────

    def set_immediate(self, key: str, value: str) -> None:
        """设置即时层记忆。"""
        self._immediate[key] = value
        self._save_immediate()

    def get_immediate(self, key: str, default: str = "") -> str:
        """获取即时层记忆。"""
        return self._immediate.get(key, default)

    def list_immediate_keys(self) -> List[str]:
        """列出所有即时层 key。"""
        return list(self._immediate.keys())

    # ─────────────────────────────────────────────
    # 近中期层操作
    # ─────────────────────────────────────────────

    def create_recent(self, content: str, tags: List[str] = None,
                      source: str = "", emotion: float = None) -> MemoryEntry:
        """创建一条近中期记忆。"""
        entry_id = self._generate_id(content)
        entry = MemoryEntry(
            id=entry_id,
            layer=MemoryLayer.RECENT,
            content=content,
            tags=tags or [],
            source=source,
            emotion=emotion,
        )
        self._recent_entries[entry_id] = entry
        self._update_index(entry)
        self._save_recent()
        return entry

    def get_recent(self, entry_id: str) -> Optional[MemoryEntry]:
        """获取一条近中期记忆。"""
        entry = self._recent_entries.get(entry_id)
        if entry:
            entry.touch()
            self._save_recent()
        return entry

    def search_recent(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """在近中期记忆中搜索。"""
        results = []
        query_lower = query.lower()
        for entry in self._recent_entries.values():
            score = 0
            # 内容匹配
            if query_lower in entry.content.lower():
                score += 2
            # 标签匹配
            for tag in entry.tags:
                if query_lower in tag.lower():
                    score += 3
            # 来源匹配
            if query_lower in entry.source.lower():
                score += 1
            if score > 0:
                entry.touch()
                results.append((score, entry))

        results.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in results[:limit]]

    def delete_recent(self, entry_id: str) -> bool:
        """删除一条近中期记忆。"""
        if entry_id in self._recent_entries:
            del self._recent_entries[entry_id]
            self._rebuild_index()
            self._save_recent()
            return True
        return False

    def list_recent_by_tag(self, tag: str) -> List[MemoryEntry]:
        """按标签列出近中期记忆。"""
        return [
            e for e in self._recent_entries.values()
            if tag in e.tags
        ]

    def get_index(self) -> Dict[str, dict]:
        """获取近中期层索引。"""
        return dict(self._recent_index)

    # ─────────────────────────────────────────────
    # 长期层操作
    # ─────────────────────────────────────────────

    def store_long_term(self, content: str, tags: List[str] = None,
                        source: str = "", emotion: float = None) -> MemoryEntry:
        """存储一条长期记忆。"""
        entry_id = self._generate_id(content + str(time.time()))
        entry = MemoryEntry(
            id=entry_id,
            layer=MemoryLayer.LONG_TERM,
            content=content,
            tags=tags or [],
            source=source,
            emotion=emotion,
        )
        self._long_term_store.append(entry)
        self._save_long_term()
        return entry

    def search_long_term(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """
        长期记忆语义检索。

        当前实现为关键词匹配 + 权重排序。
        可对接外部向量数据库（如 ChromaDB、FAISS）实现真正的语义检索。
        """
        results = []
        query_lower = query.lower()
        for entry in self._long_term_store:
            score = 0
            if query_lower in entry.content.lower():
                score += 2
            for tag in entry.tags:
                if query_lower in tag.lower():
                    score += 3
            if score > 0:
                # 加入权重衰减
                age_hours = (time.time() - entry.created_at) / 3600
                decay = 0.99 ** age_hours
                final_score = score * entry.weight * decay
                entry.touch()
                results.append((final_score, entry))

        results.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in results[:limit]]

    # ─────────────────────────────────────────────
    # 五层渐进压缩
    # ─────────────────────────────────────────────

    def compress_entry(self, entry_id: str, target_level: int,
                       summary_fn=None) -> Optional[MemoryEntry]:
        """
        对记忆条目进行渐进压缩。

        Args:
            entry_id: 记忆条目 ID
            target_level: 目标压缩等级 (1-5)
            summary_fn: 压缩函数，接受 (content, target_level) 返回压缩后文本。
                         若为 None，使用内置简单压缩。

        Returns:
            压缩后的 MemoryEntry，或 None（如果未找到）。
        """
        entry = self._recent_entries.get(entry_id)
        if not entry:
            return None

        if target_level <= entry.compression_level:
            return entry  # 已经是目标等级或更低

        if summary_fn:
            new_content = summary_fn(entry.content, target_level)
        else:
            new_content = self._default_compress(entry.content, target_level)

        entry.content = new_content
        entry.compression_level = target_level
        self._save_recent()
        return entry

    def run_compression_sweep(self, max_age_hours: float = 720,
                              summary_fn=None) -> int:
        """
        批量压缩过期记忆（渐进式）。

        根据记忆年龄自动提升压缩等级：
        - < 24h: 保持精确 (Level 1)
        - 24h ~ 72h: 轻度摘要 (Level 2)
        - 72h ~ 168h (1周): 中度压缩 (Level 3)
        - 168h ~ 720h (30天): 高度概括 (Level 4)
        - > 720h: 标签归档 (Level 5)

        Returns:
            被压缩的条目数量。
        """
        now = time.time()
        compressed = 0

        for entry in self._recent_entries.values():
            age_hours = (now - entry.created_at) / 3600

            if age_hours < 24:
                target = CompressionLevel.VERBATIM
            elif age_hours < 72:
                target = CompressionLevel.LIGHT_SUMMARY
            elif age_hours < 168:
                target = CompressionLevel.MEDIUM
            elif age_hours < 720:
                target = CompressionLevel.HIGH
            else:
                target = CompressionLevel.TAG_ONLY

            if target > entry.compression_level:
                self.compress_entry(entry.id, target, summary_fn)
                compressed += 1

        return compressed

    # ─────────────────────────────────────────────
    # 情绪联动
    # ─────────────────────────────────────────────

    def search_with_emotion(self, query: str, emotion_range: tuple = (-1.0, 1.0),
                            limit: int = 10) -> List[MemoryEntry]:
        """
        带情绪过滤的记忆检索。

        Args:
            query: 搜索关键词
            emotion_range: 情绪强度范围 (min, max)，-1.0 ~ 1.0
            limit: 返回数量上限

        Returns:
            匹配的记忆条目列表。
        """
        results = self.search_recent(query, limit=limit * 2)
        filtered = [
            e for e in results
            if e.emotion is not None and emotion_range[0] <= e.emotion <= emotion_range[1]
        ]
        return filtered[:limit]

    # ─────────────────────────────────────────────
    # 持久化
    # ─────────────────────────────────────────────

    def _init_storage(self):
        """初始化存储目录结构。"""
        self.storage_path.mkdir(parents=True, exist_ok=True)
        (self.storage_path / "immediate").mkdir(exist_ok=True)
        (self.storage_path / "recent").mkdir(exist_ok=True)
        (self.storage_path / "long_term").mkdir(exist_ok=True)

    def _load_from_disk(self):
        """从磁盘加载所有记忆。"""
        self._load_immediate()
        self._load_recent()
        self._load_long_term()

    def _load_immediate(self):
        path = self.storage_path / "immediate" / "data.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                self._immediate = json.load(f)

    def _save_immediate(self):
        path = self.storage_path / "immediate" / "data.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._immediate, f, ensure_ascii=False, indent=2)

    def _load_recent(self):
        index_path = self.storage_path / "recent" / "index.json"
        entries_path = self.storage_path / "recent" / "entries.json"

        if index_path.exists():
            with open(index_path, "r", encoding="utf-8") as f:
                self._recent_index = json.load(f)
        if entries_path.exists():
            with open(entries_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._recent_entries = {
                    k: MemoryEntry.from_dict(v) for k, v in data.items()
                }

    def _save_recent(self):
        index_path = self.storage_path / "recent" / "index.json"
        entries_path = self.storage_path / "recent" / "entries.json"

        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(self._recent_index, f, ensure_ascii=False, indent=2)
        with open(entries_path, "w", encoding="utf-8") as f:
            data = {k: v.to_dict() for k, v in self._recent_entries.items()}
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_long_term(self):
        path = self.storage_path / "long_term" / "data.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._long_term_store = [MemoryEntry.from_dict(d) for d in data]

    def _save_long_term(self):
        path = self.storage_path / "long_term" / "data.json"
        data = [e.to_dict() for e in self._long_term_store]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ─────────────────────────────────────────────
    # 内部工具
    # ─────────────────────────────────────────────

    def _generate_id(self, content: str) -> str:
        """生成记忆条目 ID。"""
        hash_input = f"{content}_{time.time()}".encode()
        return hashlib.sha256(hash_input).hexdigest()[:16]

    def _update_index(self, entry: MemoryEntry):
        """更新索引。"""
        self._recent_index[entry.id] = {
            "tags": entry.tags,
            "summary": entry.content[:100],
            "created_at": entry.created_at,
            "compression_level": entry.compression_level,
        }

    def _rebuild_index(self):
        """重建索引。"""
        self._recent_index = {}
        for entry in self._recent_entries.values():
            self._update_index(entry)

    @staticmethod
    def _default_compress(content: str, level: int) -> str:
        """内置简单压缩（实际使用时建议用 LLM 做摘要）。"""
        if level == CompressionLevel.LIGHT_SUMMARY:
            # 截取前200字
            return content[:200] + ("..." if len(content) > 200 else "")
        elif level == CompressionLevel.MEDIUM:
            # 截取前100字
            return content[:100] + ("..." if len(content) > 100 else "")
        elif level == CompressionLevel.HIGH:
            # 截取前50字
            return content[:50] + ("..." if len(content) > 50 else "")
        elif level == CompressionLevel.TAG_ONLY:
            # 仅保留前20字作为标签
            return f"[归档] {content[:20]}"
        return content
