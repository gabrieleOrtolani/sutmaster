from __future__ import annotations

import shlex
from typing import Any

from .starter_interface import StarterInterface


class SystemctlStarter(StarterInterface):
    def __init__(self, service_name: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.service_name = service_name

    def start(self) -> str:
        self.copy_files_to_host()
        self.run_post_copy_commands()
        service_name = shlex.quote(self.service_name)
        self._execute_ssh_command(f"systemctl start {service_name}")
        return f"{self.service_name} started"

    def stop(self) -> str:
        service_name = shlex.quote(self.service_name)
        self._execute_ssh_command(f"systemctl stop {service_name}")
        return f"{self.service_name} stopped"

    def status(self) -> str:
        service_name = shlex.quote(self.service_name)
        return self._execute_ssh_command(f"systemctl status {service_name} --no-pager")
