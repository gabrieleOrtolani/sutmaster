from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
import shlex
import subprocess
import tempfile
from typing import Iterable


class StarterInterface:
    def __init__(self, ssh: dict | None = None, copy_files: list[dict] | None = None, post_copy_commands: list[str] | None = None, **_: object) -> None:
        ssh = ssh or {}
        self.ssh_host = ssh.get("host", "localhost")
        self.ssh_port = int(ssh.get("port", 22))
        self.ssh_username = ssh.get("username")
        self.ssh_private_key = ssh.get("private_key")
        self.ssh_password = ssh.get("password")
        self.ssh_password_env = ssh.get("password_env")
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
        if self._resolve_ssh_password() is not None:
            args.extend(
                [
                    "-o",
                    "PreferredAuthentications=password",
                    "-o",
                    "PubkeyAuthentication=no",
                    "-o",
                    "NumberOfPasswordPrompts=1",
                ]
            )
        return args

    def _resolve_ssh_password(self) -> str | None:
        if self.ssh_password is not None:
            return str(self.ssh_password)
        if self.ssh_password_env:
            env_password = os.getenv(str(self.ssh_password_env))
            if env_password is None:
                raise ValueError(f"Environment variable not found: {self.ssh_password_env}")
            return env_password
        return None

    def _askpass_env(self) -> tuple[dict[str, str] | None, str | None]:
        password = self._resolve_ssh_password()
        if password is None:
            return None, None

        script_file = tempfile.NamedTemporaryFile(
            "w",
            suffix="-sutmaster-askpass.sh",
            delete=False,
            encoding="utf-8",
        )
        script_file.write("#!/bin/sh\nprintf '%s\\n' \"$SUTMASTER_SSH_PASSWORD\"\n")
        script_file.close()
        script_path = script_file.name
        os.chmod(script_path, 0o700)

        env = os.environ.copy()
        env.update(
            {
                "SUTMASTER_SSH_PASSWORD": password,
                "SSH_ASKPASS": script_path,
                "SSH_ASKPASS_REQUIRE": "force",
                "DISPLAY": "sutmaster:0",
            }
        )
        return env, script_path

    def _run_subprocess(self, cmd: list[str]) -> subprocess.CompletedProcess[str]:
        env, askpass_script = self._askpass_env()
        try:
            return subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                env=env,
                stdin=subprocess.DEVNULL,
            )
        finally:
            if askpass_script:
                Path(askpass_script).unlink(missing_ok=True)

    def _execute_ssh_command(self, command: str) -> str:
        cmd = ["ssh", *self._ssh_base_args(), self._target(), command]
        result = self._run_subprocess(cmd)
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
        self._run_subprocess(scp_cmd)

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
