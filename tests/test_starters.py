import tempfile
import unittest
from unittest.mock import patch

from sutmaster.docker_compose_starter import DockerComposeStarter
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


if __name__ == "__main__":
    unittest.main()
