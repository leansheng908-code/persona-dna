"""
Configuration management for Persona DNA Framework.

Handles loading, saving, and merging configuration from YAML files
and environment variables.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Optional


class Config:
    """Central configuration manager for Persona DNA."""

    DEFAULT_CONFIG = {
        "persona": {
            "name": "Assistant",
            "version": "1.0",
        },
        "memory": {
            "storage_path": "./memory_data",
            "max_immediate_items": 50,
            "max_recent_items": 500,
            "compression_levels": 5,
        },
        "map": {
            "max_nodes": 10000,
            "weight_decay_rate": 0.95,
            "decay_interval_hours": 168,  # 1 week
            "auto_associate_threshold": 0.6,
        },
        "care": {
            "enabled": True,
            "quiet_hours_start": 22,
            "quiet_hours_end": 8,
            "min_interval_minutes": 120,
            "max_daily_triggers": 5,
        },
        "growth": {
            "monthly_growth_target": (1, 2),
            "forgetting_threshold": 0.3,
            "internalization_required": 3,
            "scan_interval_hours": 24,
        },
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            config_path: Path to YAML config file. Uses defaults if None.
        """
        self._config = dict(self.DEFAULT_CONFIG)
        self._config_path = config_path

        if config_path and os.path.exists(config_path):
            self.load(config_path)

    def load(self, path: str) -> None:
        """Load configuration from a YAML file and merge with defaults."""
        with open(path, "r", encoding="utf-8") as f:
            user_config = yaml.safe_load(f) or {}

        self._config = self._deep_merge(self._config, user_config)
        self._config_path = path

    def save(self, path: Optional[str] = None) -> None:
        """Save current configuration to a YAML file."""
        save_path = path or self._config_path
        if not save_path:
            raise ValueError("No config path specified for saving.")

        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a config value by dot-separated key path.

        Example:
            config.get("memory.storage_path")
        """
        keys = key_path.split(".")
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def set(self, key_path: str, value: Any) -> None:
        """
        Set a config value by dot-separated key path.

        Example:
            config.set("memory.storage_path", "/tmp/memory")
        """
        keys = key_path.split(".")
        target = self._config
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        target[keys[-1]] = value

    def as_dict(self) -> dict:
        """Return full configuration as a dictionary."""
        return dict(self._config)

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """Deep merge override into base dict."""
        result = dict(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = Config._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
