"""Local and Docker command runners."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from opengrader.config import AssignmentConfig
from opengrader.errors import DockerUnavailableError


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Raw outcome of one command execution."""

    exit_code: int | None
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False


class LocalRunner:
    """Run commands on the host in a disposable copy of the submission.

    This provides filesystem cleanliness, not a security boundary. It should only
    be used for trusted submissions.
    """

    def run(
        self,
        submission: Path,
        command: str,
        timeout_seconds: float,
        assignment: AssignmentConfig,
    ) -> ExecutionResult:
        del assignment  # Resource limits are provided by Docker, not local mode.
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="opengrader-") as temp_dir:
            workspace = Path(temp_dir) / "submission"
            shutil.copytree(submission, workspace)
            process = subprocess.Popen(
                command,
                cwd=workspace,
                shell=True,
                executable="/bin/sh",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
            )
            try:
                stdout, stderr = process.communicate(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                # The shell may have spawned grandchildren. Killing its process
                # group keeps a timed-out command from surviving the grader.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                stdout, stderr = process.communicate()
                return ExecutionResult(
                    exit_code=None,
                    stdout=stdout,
                    stderr=stderr,
                    duration_seconds=time.monotonic() - started,
                    timed_out=True,
                )

        return ExecutionResult(
            exit_code=process.returncode,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=time.monotonic() - started,
        )


class DockerRunner:
    """Run commands in short-lived, network-disabled Docker containers."""

    def __init__(self) -> None:
        docker = shutil.which("docker")
        if docker is None:
            raise DockerUnavailableError(
                "Docker CLI was not found. Install/start Docker or use --no-docker "
                "for trusted submissions."
            )
        self.docker = docker
        try:
            subprocess.run(
                [docker, "info", "--format", "{{.ServerVersion}}"],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
        except (subprocess.SubprocessError, OSError) as exc:
            raise DockerUnavailableError(
                "Docker is installed but its daemon is unavailable. Start Docker "
                "or use --no-docker for trusted submissions."
            ) from exc

    def run(
        self,
        submission: Path,
        command: str,
        timeout_seconds: float,
        assignment: AssignmentConfig,
    ) -> ExecutionResult:
        container_name = f"opengrader-{uuid.uuid4().hex[:12]}"
        shell_command = (
            "cp -R /submission/. /workspace && "
            "export HOME=/tmp PYTHONDONTWRITEBYTECODE=1 && "
            f"{command}"
        )
        args = [
            self.docker,
            "run",
            "--rm",
            "--name",
            container_name,
            "--network",
            "none",
            "--memory",
            f"{assignment.memory_mb}m",
            "--cpus",
            str(assignment.cpus),
            "--pids-limit",
            str(assignment.pids_limit),
            "--read-only",
            "--tmpfs",
            "/tmp:rw,nosuid,size=64m",
            "--tmpfs",
            f"/workspace:rw,nosuid,size={assignment.memory_mb}m",
            "--mount",
            f"type=bind,source={submission.resolve()},target=/submission,readonly",
            "--workdir",
            "/workspace",
            assignment.image,
            "/bin/sh",
            "-lc",
            shell_command,
        ]

        started = time.monotonic()
        try:
            completed = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            subprocess.run(
                [self.docker, "rm", "-f", container_name],
                capture_output=True,
                timeout=10,
                check=False,
            )
            return ExecutionResult(
                exit_code=None,
                stdout=_timeout_text(exc.stdout),
                stderr=_timeout_text(exc.stderr),
                duration_seconds=time.monotonic() - started,
                timed_out=True,
            )

        return ExecutionResult(
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_seconds=time.monotonic() - started,
        )


def _timeout_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    return value.decode(errors="replace") if isinstance(value, bytes) else value
