"""
Proactive Care - 主动关心系统
==============================
基于规则/时间的主动触达系统。

核心能力:
- 基于时间规则的关心触发（作息、排班、日程）
- 事件驱动的关心（状态变化、里程碑）
- 关心内容模板化
- 防打扰机制（安静时段、频率控制）
"""

import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum


class TriggerType(Enum):
    """触发类型。"""
    TIME_BASED = "time_based"       # 基于时间规则
    EVENT_BASED = "event_based"     # 事件驱动
    STATE_CHANGE = "state_change"   # 状态变化
    CONDITIONAL = "conditional"     # 条件触发


class CarePriority(Enum):
    """关心优先级。"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class CareRule:
    """关心规则定义。"""
    id: str
    name: str
    trigger_type: str  # TriggerType value
    trigger_config: Dict = field(default_factory=dict)
    template: str = ""  # 关心内容模板
    priority: int = 2  # CarePriority value
    enabled: bool = True
    cooldown_minutes: int = 120
    last_triggered: float = 0
    trigger_count: int = 0
    max_daily_triggers: int = 3
    today_triggers: int = 0
    last_reset_date: str = ""  # YYYY-MM-DD

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CareRule":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class CareEvent:
    """关心的触发事件。"""
    rule_id: str
    triggered_at: float
    content: str
    priority: int
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class ProactiveCare:
    """
    主动关心系统。

    管理关心规则，评估触发条件，生成关心内容。

    典型用例:
    - 早安/晚安问候
    - 排班日提醒
    - 天气变化关心
    - 里程碑祝贺
    - 沉默过久的温暖触达
    """

    def __init__(self, storage_path: str = "./memory_data",
                 quiet_hours_start: int = 22,
                 quiet_hours_end: int = 8,
                 min_interval_minutes: int = 120,
                 max_daily_triggers: int = 5):
        self.storage_path = Path(storage_path) / "care"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self._rules: Dict[str, CareRule] = {}
        self._history: List[CareEvent] = []
        self._quiet_start = quiet_hours_start
        self._quiet_end = quiet_hours_end
        self._min_interval = min_interval_minutes
        self._max_daily = max_daily_triggers

        # 自定义条件评估器
        self._condition_evaluators: Dict[str, Callable] = {}

        self._load()

    # ─────────────────────────────────────────────
    # 规则管理
    # ─────────────────────────────────────────────

    def add_rule(self, rule: CareRule) -> None:
        """添加关心规则。"""
        self._rules[rule.id] = rule
        self._save()

    def create_rule(self, rule_id: str, name: str,
                    trigger_type: str, trigger_config: Dict,
                    template: str = "", priority: int = 2,
                    cooldown_minutes: int = 120) -> CareRule:
        """快捷创建并添加规则。"""
        rule = CareRule(
            id=rule_id,
            name=name,
            trigger_type=trigger_type,
            trigger_config=trigger_config,
            template=template,
            priority=priority,
            cooldown_minutes=cooldown_minutes,
        )
        self.add_rule(rule)
        return rule

    def remove_rule(self, rule_id: str) -> bool:
        """移除规则。"""
        if rule_id in self._rules:
            del self._rules[rule_id]
            self._save()
            return True
        return False

    def enable_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules:
            self._rules[rule_id].enabled = True
            self._save()
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules:
            self._rules[rule_id].enabled = False
            self._save()
            return True
        return False

    def list_rules(self, enabled_only: bool = False) -> List[CareRule]:
        rules = list(self._rules.values())
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        return rules

    # ─────────────────────────────────────────────
    # 触发评估
    # ─────────────────────────────────────────────

    def check_triggers(self, current_time: datetime = None) -> List[CareEvent]:
        """
        检查所有规则的触发条件。

        Args:
            current_time: 当前时间（用于测试），默认使用系统时间。

        Returns:
            触发的关心事件列表。
        """
        now = current_time or datetime.now()
        triggered = []

        # 安静时段检查
        if self._is_quiet_hour(now):
            return []

        # 每日触发计数重置
        today_str = now.strftime("%Y-%m-%d")
        for rule in self._rules.values():
            if rule.last_reset_date != today_str:
                rule.today_triggers = 0
                rule.last_reset_date = today_str

        # 全局每日上限检查
        total_today = sum(r.today_triggers for r in self._rules.values())
        if total_today >= self._max_daily:
            return []

        for rule in self._rules.values():
            if not rule.enabled:
                continue
            if rule.today_triggers >= rule.max_daily_triggers:
                continue

            # 冷却检查
            if rule.last_triggered > 0:
                elapsed = (time.time() - rule.last_triggered) / 60
                if elapsed < rule.cooldown_minutes:
                    continue

            # 全局最小间隔检查
            if self._history:
                last_event_time = max(e.triggered_at for e in self._history[-10:])
                elapsed = (time.time() - last_event_time) / 60
                if elapsed < self._min_interval:
                    continue

            # 评估触发条件
            event = self._evaluate_rule(rule, now)
            if event:
                rule.last_triggered = time.time()
                rule.trigger_count += 1
                rule.today_triggers += 1
                self._history.append(event)
                triggered.append(event)

        if triggered:
            self._save()

        return triggered

    def fire_event(self, event_type: str, payload: Dict = None) -> Optional[CareEvent]:
        """
        手动触发一个事件，检查是否有匹配规则。

        Args:
            event_type: 事件类型（如 "user_online", "weather_change"）
            payload: 事件数据

        Returns:
            如果匹配到规则则返回 CareEvent，否则 None。
        """
        payload = payload or {}
        now = datetime.now()

        for rule in self._rules.values():
            if not rule.enabled:
                continue
            if rule.trigger_type != TriggerType.EVENT_BASED.value:
                continue
            if rule.trigger_config.get("event_type") != event_type:
                continue

            # 冷却检查
            if rule.last_triggered > 0:
                elapsed = (time.time() - rule.last_triggered) / 60
                if elapsed < rule.cooldown_minutes:
                    continue

            content = self._render_template(rule.template, payload)
            event = CareEvent(
                rule_id=rule.id,
                triggered_at=time.time(),
                content=content,
                priority=rule.priority,
                metadata=payload,
            )
            rule.last_triggered = time.time()
            rule.trigger_count += 1
            self._history.append(event)
            self._save()
            return event

        return None

    # ─────────────────────────────────────────────
    # 自定义条件评估器
    # ─────────────────────────────────────────────

    def register_evaluator(self, name: str, evaluator: Callable) -> None:
        """注册自定义条件评估器。"""
        self._condition_evaluators[name] = evaluator

    # ─────────────────────────────────────────────
    # 历史记录
    # ─────────────────────────────────────────────

    def get_history(self, limit: int = 20) -> List[CareEvent]:
        """获取最近的关心历史。"""
        return self._history[-limit:]

    def get_stats(self) -> Dict:
        """获取关心系统统计。"""
        return {
            "total_rules": len(self._rules),
            "enabled_rules": sum(1 for r in self._rules.values() if r.enabled),
            "total_triggers": sum(r.trigger_count for r in self._rules.values()),
            "history_count": len(self._history),
        }

    # ─────────────────────────────────────────────
    # 内部方法
    # ─────────────────────────────────────────────

    def _evaluate_rule(self, rule: CareRule, now: datetime) -> Optional[CareEvent]:
        """评估单条规则的触发条件。"""
        trigger_type = rule.trigger_type

        if trigger_type == TriggerType.TIME_BASED.value:
            return self._evaluate_time_rule(rule, now)
        elif trigger_type == TriggerType.EVENT_BASED.value:
            return None  # 事件类型通过 fire_event 触发
        elif trigger_type == TriggerType.STATE_CHANGE.value:
            return self._evaluate_state_rule(rule, now)
        elif trigger_type == TriggerType.CONDITIONAL.value:
            return self._evaluate_conditional_rule(rule, now)

        return None

    def _evaluate_time_rule(self, rule: CareRule, now: datetime) -> Optional[CareEvent]:
        """评估基于时间的规则。"""
        config = rule.trigger_config
        time_window = config.get("time_window", "")

        if not time_window:
            return None

        # 解析时间窗口，如 "08:00-08:30"
        parts = time_window.split("-")
        if len(parts) != 2:
            return None

        try:
            start_h, start_m = map(int, parts[0].split(":"))
            end_h, end_m = map(int, parts[1].split(":"))
        except ValueError:
            return None

        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m
        current_minutes = now.hour * 60 + now.minute

        # 检查星期匹配
        weekdays = config.get("weekdays", None)  # [0-6] 0=Monday
        if weekdays is not None and now.weekday() not in weekdays:
            return None

        if start_minutes <= current_minutes <= end_minutes:
            content = self._render_template(rule.template, {
                "time": now.strftime("%H:%M"),
                "weekday": now.strftime("%A"),
                "date": now.strftime("%Y-%m-%d"),
            })
            return CareEvent(
                rule_id=rule.id,
                triggered_at=time.time(),
                content=content,
                priority=rule.priority,
            )

        return None

    def _evaluate_state_rule(self, rule: CareRule, now: datetime) -> Optional[CareEvent]:
        """评估状态变化规则。"""
        evaluator_name = rule.trigger_config.get("evaluator", "")
        if evaluator_name and evaluator_name in self._condition_evaluators:
            result = self._condition_evaluators[evaluator_name](rule, now)
            if result:
                content = self._render_template(rule.template, result if isinstance(result, dict) else {})
                return CareEvent(
                    rule_id=rule.id,
                    triggered_at=time.time(),
                    content=content,
                    priority=rule.priority,
                    metadata=result if isinstance(result, dict) else {},
                )
        return None

    def _evaluate_conditional_rule(self, rule: CareRule, now: datetime) -> Optional[CareEvent]:
        """评估条件触发规则。"""
        conditions = rule.trigger_config.get("conditions", [])
        context = rule.trigger_config.get("context", {})

        all_met = True
        for condition in conditions:
            cond_type = condition.get("type", "")
            if cond_type == "time_elapsed":
                # 检查距上次互动是否超过指定时间
                max_silence_minutes = condition.get("max_silence_minutes", 1440)
                if self._history:
                    last_trigger = max(e.triggered_at for e in self._history)
                    elapsed = (time.time() - last_trigger) / 60
                    if elapsed < max_silence_minutes:
                        all_met = False
                        break
                else:
                    all_met = False
                    break

        if all_met:
            content = self._render_template(rule.template, context)
            return CareEvent(
                rule_id=rule.id,
                triggered_at=time.time(),
                content=content,
                priority=rule.priority,
            )

        return None

    def _is_quiet_hour(self, now: datetime) -> bool:
        """检查是否在安静时段。"""
        current_hour = now.hour
        if self._quiet_start > self._quiet_end:
            # 跨午夜，如 22:00 - 08:00
            return current_hour >= self._quiet_start or current_hour < self._quiet_end
        else:
            return self._quiet_start <= current_hour < self._quiet_end

    @staticmethod
    def _render_template(template: str, context: Dict) -> str:
        """
        简单模板渲染。

        支持 {key} 占位符替换。
        """
        result = template
        for key, value in context.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result

    # ─────────────────────────────────────────────
    # 持久化
    # ─────────────────────────────────────────────

    def _load(self):
        rules_path = self.storage_path / "rules.json"
        history_path = self.storage_path / "history.json"

        if rules_path.exists():
            with open(rules_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._rules = {k: CareRule.from_dict(v) for k, v in data.items()}

        if history_path.exists():
            with open(history_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._history = [CareEvent(**d) for d in data]

    def _save(self):
        rules_path = self.storage_path / "rules.json"
        history_path = self.storage_path / "history.json"

        with open(rules_path, "w", encoding="utf-8") as f:
            json.dump({k: v.to_dict() for k, v in self._rules.items()},
                      f, ensure_ascii=False, indent=2)

        # 只保留最近100条历史
        recent_history = self._history[-100:]
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in recent_history],
                      f, ensure_ascii=False, indent=2)
