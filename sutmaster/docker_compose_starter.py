from __future__ import annotations

import tempfile
from pathlib import Path, PurePosixPath
import shlex
from typing import Any

import yaml

from .starter_interface import StarterInterface


class DockerComposeStarter(StarterInterface):
    def __init__(
        self,
        path_to_compose: str,
        container_name: str,
        override_entrypoint: bool = False,
        entrypoint_command: str = "sleep infinity",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.path_to_compose = path_to_compose
        self.container_name = container_name
        self.override_entrypoint = override_entrypoint
        self.entrypoint_command = entrypoint_command

    def _docker_compose_up(self) -> None:
        compose_path = shlex.quote(self.path_to_compose)
        self._execute_ssh_command(f"docker compose -f {compose_path} up -d")

    def _docker_compose_up_with_override(self) -> None:
        base_compose = Path(self.path_to_compose).expanduser()
        with base_compose.open("r", encoding="utf-8") as file:
            compose_data = yaml.safe_load(file) or {}

        services = compose_data.get("services", {})
        override = {
            "services": {
                service_name: {"entrypoint": ["/bin/sh", "-c", self.entrypoint_command]}
                for service_name in services
            }
        }

        with tempfile.NamedTemporaryFile("w", suffix="-override.yaml", delete=False, encoding="utf-8") as temp_file:
            yaml.safe_dump(override, temp_file)
            temp_override_path = temp_file.name

        self._copy_to_remote_host(temp_override_path, temp_override_path)
        compose_path = shlex.quote(self.path_to_compose)
        override_path = shlex.quote(temp_override_path)
        self._execute_ssh_command(
            f"docker compose -f {compose_path} -f {override_path} up -d"
        )
        self._execute_ssh_command(f"rm -f {override_path}")

    def _copy_mapping_to_container(self, src: str, dest: str) -> None:
        src_path = Path(src).expanduser().resolve()
        remote_tmp = f"/tmp/sutmaster-{src_path.name}"
        self._copy_to_remote_host(str(src_path), remote_tmp)
        container_name = shlex.quote(self.container_name)
        remote_tmp_quoted = shlex.quote(remote_tmp)
        destination = shlex.quote(dest)
        parent = shlex.quote(str(PurePosixPath(dest).parent))
        self._execute_ssh_command(f"docker exec {container_name} mkdir -p {parent}")
        self._execute_ssh_command(f"docker cp {remote_tmp_quoted} {container_name}:{destination}")
        self._execute_ssh_command(f"rm -rf {remote_tmp_quoted}")

    def copy_files_to_container(self) -> None:
        for mapping in self.copy_files_mappings:
            self._copy_mapping_to_container(mapping["src"], mapping["dest"])

    def start(self) -> str:
        if self.override_entrypoint:
            self._docker_compose_up_with_override()
        else:
            self._docker_compose_up()

        self.copy_files_to_container()
        self.run_post_copy_commands()
        return f"{self.container_name} started"

    def stop(self) -> str:
        compose_path = shlex.quote(self.path_to_compose)
        self._execute_ssh_command(f"docker compose -f {compose_path} down")
        return f"{self.container_name} stopped"

    def status(self) -> str:
        compose_path = shlex.quote(self.path_to_compose)
        return self._execute_ssh_command(f"docker compose -f {compose_path} ps")
