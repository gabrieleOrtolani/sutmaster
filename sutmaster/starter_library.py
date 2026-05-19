from __future__ import annotations

from .starter_factory import StarterFactory


class StarterLibrary:
    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def __init__(self, config_path: str | None = None) -> None:
        self.config_path = StarterFactory.resolve_config_path(config_path)

    def start_sut(self, sut_name: str) -> str:
        return StarterFactory.from_name(sut_name, self.config_path).start()

    def stop_sut(self, sut_name: str) -> str:
        return StarterFactory.from_name(sut_name, self.config_path).stop()

    def status_sut(self, sut_name: str) -> str:
        return StarterFactory.from_name(sut_name, self.config_path).status()
