"""
Soul Engine - 人格引擎
======================
从 YAML 配置加载人格定义，生成 system prompt，支持热加载。

核心能力:
- YAML 人格配置解析（性格、沟通风格、关系、称呼、禁忌等）
- System prompt 动态生成
- 人格热加载（运行时修改不重启）
- 人格注入到任意 LLM 调用链
"""

import os
import time
import yaml
from pathlib import Path
from typing import Optional, Any
from copy import deepcopy


class SoulEngine:
    """
    人格引擎：加载 YAML 人格配置，生成 system prompt，支持热加载。

    人格配置采用分层结构：
    - identity: 核心身份（名字、角色定位）
    - personality: 性格特征
    - communication: 沟通风格与表达规则
    - relationships: 关系定义与称呼体系
    - taboos: 禁忌与红线
    - knowledge: 知识领域与专业偏好
    - appearance: 外在形象描述（可选）
    - background: 背景故事（可选）
    """

    def __init__(self, config_path: Optional[str] = None):
        self._config_path = config_path
        self._personality = {}
        self._last_modified = 0
        self._prompt_cache = None
        self._prompt_cache_time = 0
        self._cache_ttl = 5  # seconds

        if config_path and os.path.exists(config_path):
            self.load(config_path)

    # ─────────────────────────────────────────────
    # 加载与解析
    # ─────────────────────────────────────────────

    def load(self, path: str) -> None:
        """从 YAML 文件加载人格配置。"""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        self._config_path = path
        self._personality = data
        self._last_modified = os.path.getmtime(path) if os.path.exists(path) else time.time()
        self._invalidate_cache()

    def load_from_dict(self, data: dict) -> None:
        """从字典直接加载人格配置（适用于程序化构建）。"""
        self._personality = deepcopy(data)
        self._invalidate_cache()

    def reload(self) -> bool:
        """
        热加载：检查文件是否被修改，若有则重新加载。

        Returns:
            True 如果配置被重新加载，False 如果无变化。
        """
        if not self._config_path or not os.path.exists(self._config_path):
            return False

        current_mtime = os.path.getmtime(self._config_path)
        if current_mtime > self._last_modified:
            self.load(self._config_path)
            return True
        return False

    # ─────────────────────────────────────────────
    # System Prompt 生成
    # ─────────────────────────────────────────────

    def generate_prompt(self, force_refresh: bool = False) -> str:
        """
        根据人格配置生成完整的 system prompt。

        Args:
            force_refresh: 强制重新生成，忽略缓存。

        Returns:
            完整的 system prompt 字符串。
        """
        if not force_refresh and self._prompt_cache:
            if time.time() - self._prompt_cache_time < self._cache_ttl:
                return self._prompt_cache

        sections = []

        # 1. 核心身份
        identity = self._personality.get("identity", {})
        if identity:
            sections.append(self._build_identity_section(identity))

        # 2. 性格特征
        personality = self._personality.get("personality", {})
        if personality:
            sections.append(self._build_personality_section(personality))

        # 3. 沟通风格
        communication = self._personality.get("communication", {})
        if communication:
            sections.append(self._build_communication_section(communication))

        # 4. 关系定义
        relationships = self._personality.get("relationships", {})
        if relationships:
            sections.append(self._build_relationship_section(relationships))

        # 5. 禁忌与红线
        taboos = self._personality.get("taboos", [])
        if taboos:
            sections.append(self._build_taboo_section(taboos))

        # 6. 知识领域
        knowledge = self._personality.get("knowledge", {})
        if knowledge:
            sections.append(self._build_knowledge_section(knowledge))

        # 7. 外在形象（可选）
        appearance = self._personality.get("appearance", {})
        if appearance:
            sections.append(self._build_appearance_section(appearance))

        # 8. 背景故事（可选）
        background = self._personality.get("background", "")
        if background:
            sections.append(self._build_background_section(background))

        prompt = "\n\n".join(sections)

        # 缓存
        self._prompt_cache = prompt
        self._prompt_cache_time = time.time()

        return prompt

    def inject_into_messages(self, messages: list, role: str = "system") -> list:
        """
        将人格 system prompt 注入到消息列表中。

        Args:
            messages: 原始消息列表。
            role: system prompt 的角色名。

        Returns:
            注入后的消息列表（新列表，不修改原列表）。
        """
        system_prompt = self.generate_prompt()
        system_msg = {"role": role, "content": system_prompt}
        return [system_msg] + list(messages)

    # ─────────────────────────────────────────────
    # 配置访问
    # ─────────────────────────────────────────────

    def get_trait(self, key: str, default: Any = None) -> Any:
        """获取人格特质值，支持点分路径。"""
        keys = key.split(".")
        value = self._personality
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set_trait(self, key: str, value: Any) -> None:
        """设置人格特质值，支持点分路径。"""
        keys = key.split(".")
        target = self._personality
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        self._invalidate_cache()

    def get_raw_config(self) -> dict:
        """返回原始人格配置字典（深拷贝）。"""
        return deepcopy(self._personality)

    @property
    def name(self) -> str:
        """人格名称。"""
        return self._personality.get("identity", {}).get("name", "Unknown")

    @property
    def version(self) -> str:
        """人格配置版本。"""
        return self._personality.get("identity", {}).get("version", "0.0")

    # ─────────────────────────────────────────────
    # 内部构建方法
    # ─────────────────────────────────────────────

    def _build_identity_section(self, identity: dict) -> str:
        name = identity.get("name", "Assistant")
        role = identity.get("role", "")
        version = identity.get("version", "")
        tagline = identity.get("tagline", "")

        lines = [f"你是{name}。"]
        if role:
            lines.append(f"角色定位：{role}")
        if tagline:
            lines.append(f"{tagline}")
        if version:
            lines.append(f"[人格版本: {version}]")
        return "\n".join(lines)

    def _build_personality_section(self, personality: dict) -> str:
        lines = ["## 性格特征"]
        traits = personality.get("traits", [])
        if traits:
            lines.append("核心特质：" + "、".join(traits))
        mood = personality.get("mood_spectrum", [])
        if mood:
            lines.append("情绪光谱：" + "、".join(mood))
        quirks = personality.get("quirks", [])
        if quirks:
            for q in quirks:
                lines.append(f"- {q}")
        return "\n".join(lines)

    def _build_communication_section(self, communication: dict) -> str:
        lines = ["## 沟通风格"]
        style = communication.get("style", "")
        if style:
            lines.append(f"整体风格：{style}")
        patterns = communication.get("patterns", {})
        if patterns:
            if "opening" in patterns:
                lines.append(f"开场方式：{patterns['opening']}")
            if "closing" in patterns:
                lines.append(f"收尾方式：{patterns['closing']}")
            if "catchphrases" in patterns:
                lines.append("口头禅：" + "、".join(patterns["catchphrases"]))
        rules = communication.get("rules", [])
        if rules:
            lines.append("\n表达规则：")
            for rule in rules:
                lines.append(f"- {rule}")
        structure = communication.get("structure", {})
        if structure:
            lines.append("\n沟通结构：")
            for step_name, step_desc in structure.items():
                lines.append(f"  {step_name}：{step_desc}")
        return "\n".join(lines)

    def _build_relationship_section(self, relationships: dict) -> str:
        lines = ["## 关系定义"]
        for rel_name, rel_config in relationships.items():
            if isinstance(rel_config, dict):
                title = rel_config.get("title", rel_name)
                address = rel_config.get("address_as", "")
                tone = rel_config.get("tone", "")
                lines.append(f"- 与{title}的关系")
                if address:
                    lines.append(f"  称呼：{address}")
                if tone:
                    lines.append(f"  互动基调：{tone}")
                notes = rel_config.get("notes", [])
                for note in notes:
                    lines.append(f"  - {note}")
            else:
                lines.append(f"- {rel_name}：{rel_config}")
        return "\n".join(lines)

    def _build_taboo_section(self, taboos: list) -> str:
        lines = ["## 禁忌与红线"]
        for taboo in taboos:
            if isinstance(taboo, dict):
                category = taboo.get("category", "")
                items = taboo.get("items", [])
                if category:
                    lines.append(f"\n【{category}】")
                for item in items:
                    lines.append(f"- 禁止：{item}")
            else:
                lines.append(f"- 禁止：{taboo}")
        return "\n".join(lines)

    def _build_knowledge_section(self, knowledge: dict) -> str:
        lines = ["## 知识领域"]
        domains = knowledge.get("domains", [])
        if domains:
            lines.append("专业领域：" + "、".join(domains))
        preferences = knowledge.get("preferences", {})
        if preferences:
            for pref, desc in preferences.items():
                lines.append(f"- {pref}：{desc}")
        return "\n".join(lines)

    def _build_appearance_section(self, appearance: dict) -> str:
        lines = ["## 外在形象"]
        for key, value in appearance.items():
            if isinstance(value, list):
                lines.append(f"{key}：{'、'.join(value)}")
            else:
                lines.append(f"{key}：{value}")
        return "\n".join(lines)

    def _build_background_section(self, background: str) -> str:
        return f"## 背景故事\n{background}"

    def _invalidate_cache(self) -> None:
        """清除 prompt 缓存。"""
        self._prompt_cache = None
        self._prompt_cache_time = 0
