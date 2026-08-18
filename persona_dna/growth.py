"""
Growth Engine - 成长引擎
========================
三层细胞模型 + 遗忘机制 + 抗侵蚀保护。

三层细胞:
- 干细胞 (Stem Cell): 不可变核心 — 身份、性格标尺、死规则、核心边界、三观锚点
- 弧光 (Arc Light): 可成长不可逆 — 价值观转变、认知突破、重大决策
- 体细胞 (Somatic Cell): 可增生/休眠 — 习惯、偏好、表达方式

成长机制:
- 自发成长：prompt 未定义的新行为 → 观察 → 内化测试
- 主人指定：直接候选 → 主人确认
- 定期扫描：每晚回顾，检测新行为模式

遗忘机制:
- 衰减曲线：长期未被激活的记忆逐渐淡化
- 差分遗忘：高情感/高频访问的内容衰减更慢

抗侵蚀保护:
- 成长与干细胞冲突 → 自动否决
- 成长节奏控制（1-2个/月健康，频繁=OOC风险）
"""

import time
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass, field, asdict
from enum import Enum


class CellType(Enum):
    """细胞类型。"""
    STEM = "stem"           # 干细胞：不可变核心
    ARC_LIGHT = "arc_light" # 弧光：可成长不可逆
    SOMATIC = "somatic"     # 体细胞：可增生/休眠


class GrowthStage(Enum):
    """成长阶段。"""
    OBSERVED = "observed"           # 观察中
    CANDIDATE = "candidate"         # 候选（等待确认）
    INTERNALIZING = "internalizing" # 内化中（遗忘测试）
    CONFIRMED = "confirmed"         # 已确认
    HIBERNATING = "hibernating"     # 休眠
    REJECTED = "rejected"          # 已否决


@dataclass
class Cell:
    """
    DNA 细胞 — 人格的最小组成单元。

    每个 cell 代表人格的一个特质/规则/习惯。
    """
    id: str
    cell_type: str          # CellType value
    content: str            # 具体内容
    category: str = ""      # 分类（identity/personality/habit/expression/...）
    stage: str = "confirmed"  # GrowthStage value
    internalize_count: int = 0  # 内化测试通过次数
    activation_count: int = 0   # 被激活/使用的次数
    last_activated: float = 0   # 最近一次激活时间
    created_at: float = field(default_factory=time.time)
    confirmed_at: float = 0     # 确认时间
    source: str = ""            # 来源（self/owner/scan）
    metadata: Dict = field(default_factory=dict)
    weight: float = 1.0         # 当前权重（用于衰减计算）
    protected: bool = False     # 是否受保护（干细胞默认 True）

    def touch(self):
        self.activation_count += 1
        self.last_activated = time.time()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Cell":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class GrowthEvent:
    """成长事件记录。"""
    id: str
    cell_id: str
    action: str         # observe / promote / hibernate / reject / protect
    description: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class GrowthEngine:
    """
    成长引擎。

    管理人格细胞的完整生命周期：观察 → 候选 → 内化测试 → 确认/否决。
    提供抗侵蚀保护，确保核心人格不被意外修改。
    """

    def __init__(self, storage_path: str = "./memory_data",
                 monthly_target: tuple = (1, 2),
                 forgetting_threshold: float = 0.3,
                 internalization_required: int = 3,
                 scan_interval_hours: float = 24):
        self.storage_path = Path(storage_path) / "growth"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self._cells: Dict[str, Cell] = {}
        self._events: List[GrowthEvent] = []
        self._monthly_target = monthly_target
        self._forgetting_threshold = forgetting_threshold
        self._internalization_required = internalization_required
        self._scan_interval_hours = scan_interval_hours

        self._load()

    # ─────────────────────────────────────────────
    # 细胞管理
    # ─────────────────────────────────────────────

    def add_cell(self, cell_id: str, cell_type: str, content: str,
                 category: str = "", source: str = "self",
                 protected: bool = None) -> Cell:
        """
        添加一个新的 DNA 细胞。

        Args:
            cell_id: 细胞唯一 ID
            cell_type: 细胞类型 (stem/arc_light/somatic)
            content: 细胞内容
            category: 分类
            source: 来源 (self/owner/scan)
            protected: 是否受保护（干细胞默认 True）

        Returns:
            创建的 Cell 对象。
        """
        if protected is None:
            protected = (cell_type == CellType.STEM.value)

        cell = Cell(
            id=cell_id,
            cell_type=cell_type,
            content=content,
            category=category,
            stage=GrowthStage.CONFIRMED.value if cell_type == CellType.STEM.value
                  else GrowthStage.OBSERVED.value,
            source=source,
            protected=protected,
            confirmed_at=time.time() if cell_type == CellType.STEM.value else 0,
        )
        self._cells[cell_id] = cell
        self._log_event(cell_id, "created", f"Created {cell_type} cell: {content[:50]}")
        self._save()
        return cell

    def get_cell(self, cell_id: str) -> Optional[Cell]:
        return self._cells.get(cell_id)

    def list_cells(self, cell_type: str = None, stage: str = None) -> List[Cell]:
        """列出细胞，可按类型和阶段过滤。"""
        results = list(self._cells.values())
        if cell_type:
            results = [c for c in results if c.cell_type == cell_type]
        if stage:
            results = [c for c in results if c.stage == stage]
        return results

    # ─────────────────────────────────────────────
    # 成长流程
    # ─────────────────────────────────────────────

    def observe(self, cell_id: str, content: str,
                category: str = "", source: str = "self") -> Cell:
        """
        观察到一个新行为模式。

        这是成长的第一步：发现 prompt 未定义的新行为。
        """
        # 检查是否已存在
        if cell_id in self._cells:
            cell = self._cells[cell_id]
            if cell.stage == GrowthStage.OBSERVED.value:
                cell.touch()
                self._save()
                return cell
            return cell

        return self.add_cell(cell_id, CellType.SOMATIC.value, content,
                             category=category, source=source)

    def promote_to_candidate(self, cell_id: str) -> Optional[Cell]:
        """
        将观察中的行为提升为候选。

        触发方式:
        - 自发：多次观察后自动提升
        - 主人指定：直接提升
        """
        cell = self._cells.get(cell_id)
        if not cell:
            return None

        # 抗侵蚀检查
        if not self._growth_compatible(cell):
            self._log_event(cell_id, "protect",
                            f"Growth rejected: conflicts with stem cells")
            cell.stage = GrowthStage.REJECTED.value
            self._save()
            return cell

        cell.stage = GrowthStage.CANDIDATE.value
        self._log_event(cell_id, "promote", f"Promoted to candidate: {cell.content[:50]}")
        self._save()
        return cell

    def owner_confirm(self, cell_id: str, cell_type: str = None) -> Optional[Cell]:
        """
        主人确认成长。

        Args:
            cell_id: 细胞 ID
            cell_type: 可选，主人指定最终细胞类型（默认保持 somatic）

        Returns:
            确认后的 Cell，或 None（如果冲突被否决）。
        """
        cell = self._cells.get(cell_id)
        if not cell:
            return None

        # 抗侵蚀检查
        if not self._growth_compatible(cell):
            self._log_event(cell_id, "protect",
                            f"Owner-specified growth rejected: stem cell conflict")
            cell.stage = GrowthStage.REJECTED.value
            self._save()
            return cell

        # 月度成长节奏检查
        if not self._within_monthly_quota():
            self._log_event(cell_id, "protect",
                            f"Growth rejected: exceeds monthly quota")
            # 不直接否决，标记为待处理
            cell.metadata["quota_exceeded"] = True
            self._save()
            return cell

        if cell_type:
            cell.cell_type = cell_type
            if cell_type == CellType.STEM.value:
                cell.protected = True

        cell.stage = GrowthStage.CONFIRMED.value
        cell.confirmed_at = time.time()
        self._log_event(cell_id, "confirm",
                        f"Owner confirmed: {cell.content[:50]} as {cell.cell_type}")
        self._save()
        return cell

    def start_internalization(self, cell_id: str) -> Optional[Cell]:
        """
        开始内化测试（遗忘测试）。

        将新模式移出 prompt → 观察是否自然回归。
        """
        cell = self._cells.get(cell_id)
        if not cell or cell.stage != GrowthStage.CANDIDATE.value:
            return None

        cell.stage = GrowthStage.INTERNALIZING.value
        cell.internalize_count = 0
        self._log_event(cell_id, "internalize_start",
                        f"Started internalization test: {cell.content[:50]}")
        self._save()
        return cell

    def record_internalization_pass(self, cell_id: str) -> Optional[Cell]:
        """
        记录一次内化测试通过（行为自然回归）。

        Returns:
            更新后的 Cell，若达到要求则自动确认。
        """
        cell = self._cells.get(cell_id)
        if not cell or cell.stage != GrowthStage.INTERNALIZING.value:
            return None

        cell.internalize_count += 1
        self._log_event(cell_id, "internalize_pass",
                        f"Internalization pass #{cell.internalize_count}")

        # 达到内化要求次数 → 自动确认
        if cell.internalize_count >= self._internalization_required:
            cell.stage = GrowthStage.CONFIRMED.value
            cell.confirmed_at = time.time()
            self._log_event(cell_id, "auto_confirm",
                            f"Auto-confirmed after {cell.internalize_count} passes")

        self._save()
        return cell

    # ─────────────────────────────────────────────
    # 休眠与唤醒
    # ─────────────────────────────────────────────

    def hibernate(self, cell_id: str) -> bool:
        """
        将体细胞设为休眠状态。

        休眠≠删除，只是暂时不活跃。
        """
        cell = self._cells.get(cell_id)
        if not cell or cell.cell_type != CellType.SOMATIC.value:
            return False
        if cell.protected:
            return False

        cell.stage = GrowthStage.HIBERNATING.value
        cell.weight = 0.1
        self._log_event(cell_id, "hibernate", f"Hibernated: {cell.content[:50]}")
        self._save()
        return True

    def wake(self, cell_id: str) -> bool:
        """唤醒休眠的体细胞。"""
        cell = self._cells.get(cell_id)
        if not cell or cell.stage != GrowthStage.HIBERNATING.value:
            return False

        cell.stage = GrowthStage.CONFIRMED.value
        cell.weight = 1.0
        cell.last_activated = time.time()
        self._log_event(cell_id, "wake", f"Woke from hibernation: {cell.content[:50]}")
        self._save()
        return True

    # ─────────────────────────────────────────────
    # 遗忘机制
    # ─────────────────────────────────────────────

    def apply_forgetting(self) -> Dict:
        """
        应用差分遗忘机制。

        - 长期未激活的体细胞权重衰减
        - 高频访问/高情感的内容衰减更慢
        - 干细胞不受遗忘影响

        Returns:
            统计信息 {"affected": N, "removed": N}
        """
        affected = 0
        removed = 0
        now = time.time()

        to_remove = []
        for cell in self._cells.values():
            # 干细胞不受遗忘影响
            if cell.cell_type == CellType.STEM.value:
                continue

            # 弧光不遗忘，只记录
            if cell.cell_type == CellType.ARC_LIGHT.value:
                continue

            # 体细胞差分遗忘
            if cell.stage == GrowthStage.CONFIRMED.value:
                age_hours = (now - cell.confirmed_at) / 3600 if cell.confirmed_at else 1
                since_activation = (now - cell.last_activated) / 3600 if cell.last_activated else age_hours

                # 差分因子：激活频率越高，衰减越慢
                activation_factor = 1.0 / (1.0 + cell.activation_count * 0.1)
                decay_rate = 0.95 ** (since_activation / 168 * activation_factor)  # 168h = 1 week

                cell.weight *= decay_rate
                affected += 1

                # 低于阈值 → 休眠
                if cell.weight < self._forgetting_threshold:
                    cell.stage = GrowthStage.HIBERNATING.value
                    self._log_event(cell.id, "forget_hibernate",
                                    f"Weight dropped to {cell.weight:.3f}, hibernated")

        # 清理已否决的和权重极低的休眠体细胞
        for cell_id, cell in self._cells.items():
            if (cell.stage == GrowthStage.REJECTED.value or
                (cell.stage == GrowthStage.HIBERNATING.value and cell.weight < 0.01)):
                to_remove.append(cell_id)

        for cell_id in to_remove:
            del self._cells[cell_id]
            removed += 1

        if affected > 0 or removed > 0:
            self._save()

        return {"affected": affected, "removed": removed}

    # ─────────────────────────────────────────────
    # 抗侵蚀保护
    # ─────────────────────────────────────────────

    def _growth_compatible(self, new_cell: Cell) -> bool:
        """
        检查新成长是否与干细胞冲突。

        成长与干细胞冲突 → 自动否决（铁律）。
        """
        # 如果新细胞本身就是干细胞，允许
        if new_cell.cell_type == CellType.STEM.value:
            return True

        # 检查与所有干细胞的冲突
        for cell in self._cells.values():
            if cell.cell_type != CellType.STEM.value:
                continue
            if not cell.protected:
                continue

            # 简单冲突检测：同类别 + 内容相似度高
            if cell.category == new_cell.category:
                # 内容关键词重叠检测
                stem_words = set(cell.content.lower().split())
                new_words = set(new_cell.content.lower().split())
                if stem_words and new_words:
                    overlap = len(stem_words & new_words) / min(len(stem_words), len(new_words))
                    if overlap > 0.5:
                        return False

        return True

    def _within_monthly_quota(self) -> bool:
        """检查本月成长是否在目标范围内。"""
        now = datetime.now()
        month_start = datetime(now.year, now.month, 1).timestamp()

        month_confirms = sum(
            1 for cell in self._cells.values()
            if cell.confirmed_at >= month_start
            and cell.cell_type != CellType.STEM.value
        )

        return month_confirms < self._monthly_target[1] + 1  # 允许+1的缓冲

    # ─────────────────────────────────────────────
    # 定期扫描
    # ─────────────────────────────────────────────

    def scan_for_patterns(self, behavior_log: List[Dict]) -> List[Cell]:
        """
        定期扫描行为日志，检测新的成长模式。

        Args:
            behavior_log: 行为记录列表，每条包含 {"action": str, "context": str, "timestamp": float}

        Returns:
            检测到的新行为模式列表。
        """
        new_patterns = []

        # 提取所有已有的确认行为
        known_behaviors = set()
        for cell in self._cells.values():
            if cell.stage in (GrowthStage.CONFIRMED.value, GrowthStage.INTERNALIZING.value):
                known_behaviors.add(cell.content.lower().strip())

        # 检测未定义的新行为
        for behavior in behavior_log:
            action = behavior.get("action", "").lower().strip()
            if action and action not in known_behaviors:
                cell_id = f"scan_{int(time.time())}_{len(new_patterns)}"
                pattern = self.observe(cell_id, behavior.get("action", ""),
                                       category="scanned", source="scan")
                new_patterns.append(pattern)

        return new_patterns

    # ─────────────────────────────────────────────
    # 状态导出
    # ─────────────────────────────────────────────

    def get_state_snapshot(self) -> Dict:
        """获取完整的成长状态快照。"""
        return {
            "cells": {k: v.to_dict() for k, v in self._cells.items()},
            "stats": {
                "total_cells": len(self._cells),
                "stem_cells": len(self.list_cells(cell_type=CellType.STEM.value)),
                "arc_light_cells": len(self.list_cells(cell_type=CellType.ARC_LIGHT.value)),
                "somatic_cells": len(self.list_cells(cell_type=CellType.SOMATIC.value)),
                "observed": len(self.list_cells(stage=GrowthStage.OBSERVED.value)),
                "candidates": len(self.list_cells(stage=GrowthStage.CANDIDATE.value)),
                "internalizing": len(self.list_cells(stage=GrowthStage.INTERNALIZING.value)),
                "confirmed": len(self.list_cells(stage=GrowthStage.CONFIRMED.value)),
                "hibernating": len(self.list_cells(stage=GrowthStage.HIBERNATING.value)),
            },
            "recent_events": [e.to_dict() for e in self._events[-20:]],
        }

    # ─────────────────────────────────────────────
    # 内部工具
    # ─────────────────────────────────────────────

    def _log_event(self, cell_id: str, action: str, description: str):
        event = GrowthEvent(
            id=f"evt_{int(time.time() * 1000)}",
            cell_id=cell_id,
            action=action,
            description=description,
        )
        self._events.append(event)
        # 只保留最近200条事件
        if len(self._events) > 200:
            self._events = self._events[-200:]

    def _load(self):
        cells_path = self.storage_path / "cells.json"
        events_path = self.storage_path / "events.json"

        if cells_path.exists():
            with open(cells_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._cells = {k: Cell.from_dict(v) for k, v in data.items()}

        if events_path.exists():
            with open(events_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._events = [GrowthEvent(**d) for d in data]

    def _save(self):
        cells_path = self.storage_path / "cells.json"
        events_path = self.storage_path / "events.json"

        with open(cells_path, "w", encoding="utf-8") as f:
            json.dump({k: v.to_dict() for k, v in self._cells.items()},
                      f, ensure_ascii=False, indent=2)

        with open(events_path, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in self._events[-200:]],
                      f, ensure_ascii=False, indent=2)
