import tempfile
import unittest
import subprocess
from unittest.mock import patch

from sutmaster.docker_compose_starter import DockerComposeStarter
from sutmaster.starter_interface import StarterInterface
from sutmaster.starter_factory import StarterFactory
from sutmaster.systemctl_starter import SystemctlStarter


class DockerComposeStarterTests(unittest.TestCase):
    def test_start_uses_override_then_copy_then_post_copy(self):
        order = []

        class FakeStarter(DockerComposeStarter):
            def _docker_compose_up_with_override(self):
                order.append("up_with_override")

            def _docker_compose_up(self):
                order.append("up")

            def copy_files_to_container(self):
                order.append("copy")

            def run_post_copy_commands(self, commands=None):
                order.append("post")

        starter = FakeStarter(
            path_to_compose="/tmp/docker-compose.yml",
            container_name="sut",
            override_entrypoint=True,
            ssh={"username": "user"},
            copy_files=[{"src": "/tmp/a", "dest": "/home/birra/config.json"}],
            post_copy_commands=["docker exec sut python app.py"],
        )

        starter.start()

        self.assertEqual(order, ["up_with_override", "copy", "post"])


class SystemctlStarterTests(unittest.TestCase):
    def test_start_copies_then_runs_post_copy_then_starts_service(self):
        order = []

        class FakeStarter(SystemctlStarter):
            def copy_files_to_host(self):
                order.append("copy")

            def run_post_copy_commands(self, commands=None):
                order.append("post")

            def _execute_ssh_command(self, command):
                order.append(command)
                return ""

        starter = FakeStarter(service_name="sut-b", ssh={"username": "admin"})
        starter.start()

        self.assertEqual(order, ["copy", "post", "systemctl start sut-b"])


class StarterFactoryTests(unittest.TestCase):
    def test_factory_returns_correct_starter_types(self):
        docker = StarterFactory.get_starter(
            "docker-compose",
            path_to_compose="/tmp/docker-compose.yml",
            container_name="sut",
            ssh={"username": "u"},
        )
        systemd = StarterFactory.get_starter("systemctl", service_name="svc", ssh={"username": "u"})

        self.assertIsInstance(docker, DockerComposeStarter)
        self.assertIsInstance(systemd, SystemctlStarter)

    def test_from_name_uses_yaml_configuration(self):
        content = """
SUTs:
  SUT-B:
    type: systemctl
    service_name: sut-b
    ssh:
      username: admin
"""
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as file:
            file.write(content)
            config_path = file.name

        starter = StarterFactory.from_name("SUT-B", config_path=config_path)
        self.assertIsInstance(starter, SystemctlStarter)

    def test_from_name_uses_env_var_configuration_when_config_path_not_provided(self):
        content = """
SUTs:
  SUT-B:
    type: systemctl
    service_name: sut-b
    ssh:
      username: admin
"""
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as file:
            file.write(content)
            config_path = file.name

        with patch.dict("os.environ", {"SUTMASTER_YAML": config_path}):
            starter = StarterFactory.from_name("SUT-B")
        self.assertIsInstance(starter, SystemctlStarter)

    def test_from_name_does_not_mutate_config(self):
        config = {
            "SUTs": {
                "SUT-B": {
                    "type": "systemctl",
                    "service_name": "sut-b",
                    "ssh": {"username": "admin"},
                }
            }
        }

        with patch("sutmaster.starter_factory.StarterFactory.load_config", return_value=config):
            StarterFactory.from_name("SUT-B")
            starter = StarterFactory.from_name("SUT-B")

        self.assertIsInstance(starter, SystemctlStarter)


class StarterInterfaceSshPasswordTests(unittest.TestCase):
    def test_password_env_missing_raises_value_error(self):
        starter = SystemctlStarter(service_name="svc", ssh={"username": "u", "password_env": "MISSING_PASSWORD_VAR"})
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(ValueError, "Environment variable not found: MISSING_PASSWORD_VAR"):
                starter._resolve_ssh_password()

    def test_ssh_base_args_include_password_auth_options(self):
        starter = SystemctlStarter(service_name="svc", ssh={"username": "u", "password": "secret"})
        args = starter._ssh_base_args()
        self.assertIn("PreferredAuthentications=password", args)
        self.assertIn("PubkeyAuthentication=no", args)
        self.assertIn("NumberOfPasswordPrompts=1", args)

    def test_execute_ssh_command_uses_askpass_when_password_env_is_set(self):
        starter = SystemctlStarter(service_name="svc", ssh={"username": "u", "password_env": "TEST_SSH_PASSWORD"})
        completed = subprocess.CompletedProcess(args=["ssh"], returncode=0, stdout="ok", stderr="")
        with patch.dict("os.environ", {"TEST_SSH_PASSWORD": "secret"}, clear=True):
            with patch("subprocess.run", return_value=completed) as mocked_run:
                output = starter._execute_ssh_command("echo ok")

        self.assertEqual(output, "ok")
        _, kwargs = mocked_run.call_args
        self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
        self.assertIn("SSH_ASKPASS", kwargs["env"])
        self.assertEqual(kwargs["env"]["SUTMASTER_SSH_PASSWORD"], "secret")


if __name__ == "__main__":
    unittest.main()
