"""Persistent grading-job worker that runs outside HTTP request handlers."""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

from opengrader.config import load_assignment
from opengrader.grader import Runner, grade_assignment
from opengrader.repository import JobRepository
from opengrader.results import write_results
from opengrader.runners import DockerRunner, LocalRunner
from opengrader.submissions import discover_submissions, select_submissions

RunnerFactory = Callable[[bool], Runner]


def default_runner_factory(no_docker: bool) -> Runner:
    return LocalRunner() if no_docker else DockerRunner()


class JobWorker:
    """Claim durable jobs and execute them on one managed background thread."""

    def __init__(
        self,
        repository: JobRepository,
        *,
        output_root: Path,
        poll_interval: float = 0.25,
        runner_factory: RunnerFactory = default_runner_factory,
        worker_actor: str = "worker:local",
    ) -> None:
        if poll_interval <= 0:
            raise ValueError("poll_interval must be positive")
        self.repository = repository
        self.output_root = output_root
        self.poll_interval = poll_interval
        self.runner_factory = runner_factory
        self.worker_actor = worker_actor
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="opengrader-job-worker",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        self._wake_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def notify(self) -> None:
        self._wake_event.set()

    def run_once(self) -> bool:
        """Process at most one queued job and report whether one was claimed."""

        job = self.repository.claim_next_job(worker_actor=self.worker_actor)
        if job is None:
            return False

        try:
            request = job.request
            assignment = load_assignment(request.assignment_file)
            submissions = select_submissions(
                discover_submissions(request.submissions_dir),
                request.submission_patterns,
            )
            runner = self.runner_factory(request.no_docker)
            result = grade_assignment(
                assignment,
                submissions,
                runner,
                "local" if request.no_docker else "docker",
                workers=request.workers,
                retries=request.retries,
            )
            json_path, markdown_path, csv_path = write_results(
                result, self.output_root / job.id
            )
            self.repository.complete_job(
                job.id,
                result=result,
                reports={
                    "json": str(json_path.resolve()),
                    "markdown": str(markdown_path.resolve()),
                    "csv": str(csv_path.resolve()),
                },
                worker_actor=self.worker_actor,
            )
        except Exception as exc:
            self.repository.fail_job(
                job.id,
                error=f"{type(exc).__name__}: {exc}",
                worker_actor=self.worker_actor,
            )
        return True

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            processed = self.run_once()
            if not processed:
                self._wake_event.wait(self.poll_interval)
                self._wake_event.clear()
