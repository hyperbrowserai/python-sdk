from tests.helpers.config import create_client
from tests.helpers.sandbox import (
    default_sandbox_params,
    stop_sandbox_if_running,
    wait_for_runtime_ready,
)

client = create_client()


def test_sandbox_sudo_e2e():
    sandbox = None

    try:
        sandbox = client.sandboxes.create(default_sandbox_params("py-sdk-sudo"))
        wait_for_runtime_ready(sandbox)

        path = "/tmp/sdk-sudo-check.txt"

        runtime_user = sandbox.exec(
            {
                "command": "bash",
                "args": ["-lc", "whoami && id -u && id -g"],
            }
        )
        assert runtime_user.exit_code == 0
        assert "ubuntu" in runtime_user.stdout
        assert "1000" in runtime_user.stdout

        direct_chown = sandbox.exec(
            {
                "command": "bash",
                "args": [
                    "-lc",
                    " && ".join(
                        [
                            f'printf "sudo-check" > "{path}"',
                            f'chown root:root "{path}"',
                        ]
                    ),
                ],
            }
        )
        assert direct_chown.exit_code != 0
        assert "operation not permitted" in direct_chown.stderr.lower()

        sudo_result = sandbox.exec(
            {
                "command": "bash",
                "args": [
                    "-lc",
                    " && ".join(
                        [
                            "sudo -n whoami",
                            f'sudo -n chown root:root "{path}"',
                            f"stat -c '%U:%G' \"{path}\"",
                        ]
                    ),
                ],
            }
        )
        assert sudo_result.exit_code == 0
        assert "root" in sudo_result.stdout
        assert "root:root" in sudo_result.stdout
    finally:
        stop_sandbox_if_running(sandbox)
