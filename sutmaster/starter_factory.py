from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from .docker_compose_starter import DockerComposeStarter
from .systemctl_starter import SystemctlStarter


class StarterFactory:
    DEFAULT_CONFIG_PATH = "sut-config.yaml"
    CONFIG_ENV_VAR = "SUTMASTER_YAML"

    @classmethod
    def resolve_config_path(cls, config_path: str | None = None) -> str:
        if config_path:
            return config_path
        return os.getenv(cls.CONFIG_ENV_VAR, cls.DEFAULT_CONFIG_PATH)

    @staticmethod
    def get_starter(starter_type: str, **config: Any):
        if starter_type == "docker-compose":
            return DockerComposeStarter(**config)
        if starter_type == "systemctl":
            return SystemctlStarter(**config)
        raise ValueError(f"Unsupported starter type: {starter_type}")

    @staticmethod
    def load_config(config_path: str | None = None) -> dict[str, Any]:
        resolved_path = StarterFactory.resolve_config_path(config_path)
        with Path(resolved_path).expanduser().open("r", encoding="utf-8") as config_file:
            return yaml.safe_load(config_file) or {}

    @classmethod
    def from_name(cls, sut_name: str, config_path: str | None = None):
        config = cls.load_config(config_path)
        suts = config.get("SUTs", {})
        sut_config = suts.get(sut_name)
        if sut_config is None:
            raise KeyError(f"SUT not found: {sut_name}")
        sut_config = dict(sut_config)
        starter_type = sut_config.pop("type")
        return cls.get_starter(starter_type, **sut_config)
