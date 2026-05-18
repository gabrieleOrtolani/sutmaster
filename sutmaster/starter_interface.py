from __future__ import annotations

from pathlib import Path, PurePosixPath
import shlex
import subprocess
from typing import Iterable


class StarterInterface:
    def __init__(self, ssh: dict | None = None, copy_files: list[dict] | None = None, post_copy_commands: list[str] | None = None, **_: object) -> None:
        ssh = ssh or {}
        self.ssh_host = ssh.get("host", "localhost")
        self.ssh_port = int(ssh.get("port", 22))
        self.ssh_username = ssh.get("username")
        self.ssh_private_key = ssh.get("private_key")
        self.copy_files_mappings = copy_files or []
        self.post_copy_commands = post_copy_commands or []

    def _target(self) -> str:
        if not self.ssh_username:
            raise ValueError("ssh.username is required")
        return f"{self.ssh_username}@{self.ssh_host}"

    def _ssh_base_args(self) -> list[str]:
        args = ["-p", str(self.ssh_port)]
        if self.ssh_private_key:
            args.extend(["-i", str(Path(self.ssh_private_key).expanduser())])
        return args

    def _execute_ssh_command(self, command: str) -> str:
        cmd = ["ssh", *self._ssh_base_args(), self._target(), command]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return result.stdout

    def _copy_to_remote_host(self, src: str, dest: str) -> None:
        src_path = Path(src).expanduser().resolve()
        if not src_path.exists():
            raise FileNotFoundError(f"Source path does not exist: {src_path}")

        remote_parent = str(PurePosixPath(dest).parent)
        self._execute_ssh_command(f"mkdir -p {shlex.quote(remote_parent)}")

        scp_cmd = ["scp", *self._ssh_base_args()]
        if src_path.is_dir():
            scp_cmd.append("-r")
        scp_cmd.extend([str(src_path), f"{self._target()}:{dest}"])
        subprocess.run(scp_cmd, check=True, capture_output=True, text=True)

    def copy_files_to_host(self) -> None:
        for mapping in self.copy_files_mappings:
            self._copy_to_remote_host(mapping["src"], mapping["dest"])

    def run_post_copy_commands(self, commands: Iterable[str] | None = None) -> None:
        for command in commands or self.post_copy_commands:
            self._execute_ssh_command(command)

    def start(self) -> str:
        raise NotImplementedError

    def stop(self) -> str:
        raise NotImplementedError

    def status(self) -> str:
        raise NotImplementedError
