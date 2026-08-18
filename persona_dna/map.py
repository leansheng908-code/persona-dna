"""
Concept Map - 概念关联图谱
==========================
节点(概念) + 边(关系) + 坐标，构建概念关联网络。

核心能力:
- 概念节点创建与管理
- 关系边权重计算
- 关键词检索 → 匹配节点 → 返回关联概念
- 自动关联新记忆
- 权重衰减机制
"""

import time
import math
import json
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Set
from dataclasses import dataclass, field, asdict


@dataclass
class ConceptNode:
    """概念图谱节点。"""
    id: str
    label: str
    category: str = ""
    x: float = 0.0
    y: float = 0.0
    metadata: Dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    access_count: int = 0
    weight: float = 1.0
    memory_ids: List[str] = field(default_factory=list)  # 关联的记忆条目 ID

    def touch(self):
        self.access_count += 1

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ConceptNode":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ConceptEdge:
    """概念图谱边（关系）。"""
    source_id: str
    target_id: str
    relation: str  # 关系类型：associated, causes, part_of, similar, etc.
    weight: float = 1.0
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ConceptEdge":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ConceptMap:
    """
    概念关联图谱。

    节点代表概念，边代表关系，支持：
    - 关键词检索 → 匹配节点 → 返回关联概念
    - 自动关联新记忆
    - 权重衰减
    """

    def __init__(self, storage_path: str = "./memory_data",
                 weight_decay_rate: float = 0.95,
                 decay_interval_hours: float = 168,
                 auto_associate_threshold: float = 0.6):
        self.storage_path = Path(storage_path) / "concept_map"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self._nodes: Dict[str, ConceptNode] = {}
        self._edges: List[ConceptEdge] = []
        self._weight_decay_rate = weight_decay_rate
        self._decay_interval_hours = decay_interval_hours
        self._auto_threshold = auto_associate_threshold

        self._load()

    # ─────────────────────────────────────────────
    # 节点操作
    # ─────────────────────────────────────────────

    def add_node(self, node_id: str, label: str, category: str = "",
                 x: float = 0.0, y: float = 0.0,
                 metadata: Dict = None, memory_ids: List[str] = None) -> ConceptNode:
        """添加概念节点。"""
        node = ConceptNode(
            id=node_id,
            label=label,
            category=category,
            x=x,
            y=y,
            metadata=metadata or {},
            memory_ids=memory_ids or [],
        )
        self._nodes[node_id] = node
        self._save()
        return node

    def get_node(self, node_id: str) -> Optional[ConceptNode]:
        """获取节点。"""
        return self._nodes.get(node_id)

    def remove_node(self, node_id: str) -> bool:
        """移除节点及其相关边。"""
        if node_id not in self._nodes:
            return False
        del self._nodes[node_id]
        self._edges = [
            e for e in self._edges
            if e.source_id != node_id and e.target_id != node_id
        ]
        self._save()
        return True

    def list_nodes(self, category: str = None) -> List[ConceptNode]:
        """列出所有节点，可按类别过滤。"""
        if category:
            return [n for n in self._nodes.values() if n.category == category]
        return list(self._nodes.values())

    # ─────────────────────────────────────────────
    # 边操作
    # ─────────────────────────────────────────────

    def add_edge(self, source_id: str, target_id: str,
                 relation: str = "associated", weight: float = 1.0) -> Optional[ConceptEdge]:
        """添加关系边。"""
        if source_id not in self._nodes or target_id not in self._nodes:
            return None

        # 检查是否已存在
        for edge in self._edges:
            if (edge.source_id == source_id and edge.target_id == target_id):
                edge.weight = max(edge.weight, weight)
                edge.last_accessed = time.time()
                self._save()
                return edge
            if (edge.source_id == target_id and edge.target_id == source_id):
                edge.weight = max(edge.weight, weight)
                edge.last_accessed = time.time()
                self._save()
                return edge

        edge = ConceptEdge(
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            weight=weight,
        )
        self._edges.append(edge)
        self._save()
        return edge

    def get_edges(self, node_id: str) -> List[ConceptEdge]:
        """获取与节点相关的所有边。"""
        return [
            e for e in self._edges
            if e.source_id == node_id or e.target_id == node_id
        ]

    # ─────────────────────────────────────────────
    # 检索
    # ─────────────────────────────────────────────

    def search(self, query: str, depth: int = 2, limit: int = 20) -> Dict:
        """
        关键词检索：输入关键词 → 匹配节点 → 返回关联概念网络。

        Args:
            query: 搜索关键词
            depth: 关联深度（1=直接关联，2=二跳关联）
            limit: 返回节点数量上限

        Returns:
            {
                "matched_nodes": [直接匹配的节点],
                "related_nodes": [关联节点],
                "edges": [相关边],
                "subgraph": {完整的子图数据}
            }
        """
        query_lower = query.lower()

        # 1. 匹配节点
        matched = []
        for node in self._nodes.values():
            score = 0
            if query_lower == node.label.lower():
                score = 10
            elif query_lower in node.label.lower():
                score = 5
            for tag in node.metadata.get("tags", []):
                if query_lower in tag.lower():
                    score += 3
            if score > 0:
                node.touch()
                matched.append((score, node))

        matched.sort(key=lambda x: x[0], reverse=True)
        matched_nodes = [n for _, n in matched[:limit]]

        if not matched_nodes:
            return {"matched_nodes": [], "related_nodes": [], "edges": [], "subgraph": {}}

        # 2. 广度优先扩展关联
        matched_ids: Set[str] = {n.id for n in matched_nodes}
        related_ids: Set[str] = set()
        result_edges: List[ConceptEdge] = []

        frontier = set(matched_ids)
        for d in range(depth):
            next_frontier = set()
            for edge in self._edges:
                if edge.source_id in frontier and edge.target_id not in matched_ids:
                    related_ids.add(edge.target_id)
                    next_frontier.add(edge.target_id)
                    result_edges.append(edge)
                elif edge.target_id in frontier and edge.source_id not in matched_ids:
                    related_ids.add(edge.source_id)
                    next_frontier.add(edge.source_id)
                    result_edges.append(edge)
            frontier = next_frontier

        related_nodes = [
            self._nodes[nid] for nid in related_ids
            if nid in self._nodes
        ][:limit - len(matched_nodes)]

        # 3. 收集匹配节点之间的边
        for edge in self._edges:
            if edge.source_id in matched_ids and edge.target_id in matched_ids:
                if edge not in result_edges:
                    result_edges.append(edge)

        # 4. 构建子图
        all_node_ids = matched_ids | {n.id for n in related_nodes}
        subgraph = {
            "nodes": [self._nodes[nid].to_dict() for nid in all_node_ids if nid in self._nodes],
            "edges": [e.to_dict() for e in result_edges],
        }

        self._save()

        return {
            "matched_nodes": [n.to_dict() for n in matched_nodes],
            "related_nodes": [n.to_dict() for n in related_nodes],
            "edges": [e.to_dict() for e in result_edges],
            "subgraph": subgraph,
        }

    # ─────────────────────────────────────────────
    # 自动关联
    # ─────────────────────────────────────────────

    def auto_associate(self, memory_id: str, content: str,
                       tags: List[str] = None) -> List[ConceptEdge]:
        """
        自动将新记忆与已有概念关联。

        通过关键词匹配计算关联度，超过阈值的自动建立关系边。

        Args:
            memory_id: 记忆条目 ID
            content: 记忆内容
            tags: 记忆标签

        Returns:
            新创建的关系边列表。
        """
        tags = tags or []
        content_lower = content.lower()
        new_edges = []

        for node in self._nodes.values():
            score = 0.0

            # 标签匹配
            node_tags = node.metadata.get("tags", [])
            for tag in tags:
                if tag.lower() in [t.lower() for t in node_tags]:
                    score += 0.5

            # 内容关键词匹配
            label_words = set(node.label.lower().split())
            content_words = set(content_lower.split())
            overlap = label_words & content_words
            if overlap:
                score += 0.3 * min(len(overlap) / max(len(label_words), 1), 1.0)

            if score >= self._auto_threshold:
                # 关联记忆到节点
                if memory_id not in node.memory_ids:
                    node.memory_ids.append(memory_id)

                edge = self.add_edge(
                    source_id=node.id,
                    target_id=memory_id,
                    relation="associated",
                    weight=score,
                )
                if edge:
                    new_edges.append(edge)

        if new_edges:
            self._save()

        return new_edges

    # ─────────────────────────────────────────────
    # 权重衰减
    # ─────────────────────────────────────────────

    def apply_decay(self) -> int:
        """
        应用权重衰减。

        基于时间和访问频率对边权重进行衰减。
        差分遗忘：被频繁访问的关系衰减更慢。

        Returns:
            受影响的边数量。
        """
        now = time.time()
        affected = 0

        for edge in self._edges:
            age_hours = (now - edge.last_accessed) / 3600
            if age_hours < self._decay_interval_hours:
                continue

            # 差分遗忘：访问次数越多衰减越慢
            access_factor = 1.0 / (1.0 + math.log1p(edge.weight * 10))
            periods = age_hours / self._decay_interval_hours
            decay = self._weight_decay_rate ** (periods * access_factor)
            edge.weight *= decay

            if edge.weight < 0.01:
                edge.weight = 0.01

            affected += 1

        # 移除权重过低的边
        before_count = len(self._edges)
        self._edges = [e for e in self._edges if e.weight > 0.01]
        removed = before_count - len(self._edges)

        if affected > 0 or removed > 0:
            self._save()

        return affected

    # ─────────────────────────────────────────────
    # 持久化
    # ─────────────────────────────────────────────

    def _load(self):
        nodes_path = self.storage_path / "nodes.json"
        edges_path = self.storage_path / "edges.json"

        if nodes_path.exists():
            with open(nodes_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._nodes = {k: ConceptNode.from_dict(v) for k, v in data.items()}

        if edges_path.exists():
            with open(edges_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._edges = [ConceptEdge.from_dict(d) for d in data]

    def _save(self):
        nodes_path = self.storage_path / "nodes.json"
        edges_path = self.storage_path / "edges.json"

        with open(nodes_path, "w", encoding="utf-8") as f:
            json.dump({k: v.to_dict() for k, v in self._nodes.items()},
                      f, ensure_ascii=False, indent=2)

        with open(edges_path, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in self._edges],
                      f, ensure_ascii=False, indent=2)

    # ─────────────────────────────────────────────
    # 统计
    # ─────────────────────────────────────────────

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    def stats(self) -> Dict:
        """返回图谱统计信息。"""
        categories = {}
        for node in self._nodes.values():
            cat = node.category or "uncategorized"
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total_nodes": self.node_count,
            "total_edges": self.edge_count,
            "categories": categories,
            "avg_weight": (
                sum(e.weight for e in self._edges) / len(self._edges)
                if self._edges else 0
            ),
        }
