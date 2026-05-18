from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .docker_compose_starter import DockerComposeStarter
from .systemctl_starter import SystemctlStarter


class StarterFactory:
    @staticmethod
    def get_starter(starter_type: str, **config: Any):
        if starter_type == "docker-compose":
            return DockerComposeStarter(**config)
        if starter_type == "systemctl":
            return SystemctlStarter(**config)
        raise ValueError(f"Unsupported starter type: {starter_type}")

    @staticmethod
    def load_config(config_path: str = "sut-config.yaml") -> dict[str, Any]:
        with Path(config_path).expanduser().open("r", encoding="utf-8") as config_file:
            return yaml.safe_load(config_file) or {}

    @classmethod
    def from_name(cls, sut_name: str, config_path: str = "sut-config.yaml"):
        config = cls.load_config(config_path)
        suts = config.get("SUTs", {})
        sut_config = suts.get(sut_name)
        if sut_config is None:
            raise KeyError(f"SUT not found: {sut_name}")
        sut_config = dict(sut_config)
        starter_type = sut_config.pop("type")
        return cls.get_starter(starter_type, **sut_config)
