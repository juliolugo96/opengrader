from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import opengrader.worker as worker_module
from opengrader.worker import JobWorker

pytestmark = pytest.mark.unit


class RepositorySpy:
    def __init__(self, job: object | None = None) -> None:
        self.job = job
        self.claim_actors: list[str] = []
        self.completed: list[dict[str, Any]] = []
        self.failed: list[dict[str, Any]] = []

    def claim_next_job(self, worker_actor: str) -> object | None:
        self.claim_actors.append(worker_actor)
        job, self.job = self.job, None
        return job

    def complete_job(self, job_id: str, **values: Any) -> None:
        self.completed.append({"job_id": job_id, **values})

    def fail_job(self, job_id: str, **values: Any) -> None:
        self.failed.append({"job_id": job_id, **values})


def test_worker_defaults_and_poll_interval_boundary(tmp_path: Path) -> None:
    repository = RepositorySpy()
    worker = JobWorker(repository, output_root=tmp_path)  # type: ignore[arg-type]

    assert worker.repository is repository
    assert worker.output_root == tmp_path
    assert worker.poll_interval == 0.25
    assert worker.worker_actor == "worker:local"
    assert worker.runner_factory is worker_module.default_runner_factory
    assert worker._thread is None
    assert worker._stop_event.is_set() is False
    assert worker._wake_event.is_set() is False

    with pytest.raises(ValueError, match="^poll_interval must be positive$"):
        JobWorker(repository, output_root=tmp_path, poll_interval=0)  # type: ignore[arg-type]


def test_start_creates_one_named_daemon_thread(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    created: list[FakeThread] = []

    class FakeThread:
        def __init__(self, **options: Any) -> None:
            self.options = options
            self.started = 0
            self.alive = False
            created.append(self)

        def is_alive(self) -> bool:
            return self.alive

        def start(self) -> None:
            self.started += 1
            self.alive = True

    monkeypatch.setattr(worker_module.threading, "Thread", FakeThread)
    worker = JobWorker(RepositorySpy(), output_root=tmp_path)  # type: ignore[arg-type]
    worker._stop_event.set()

    worker.start()
    worker.start()

    assert len(created) == 1
    thread = created[0]
    assert thread.options["target"] == worker._run_loop
    assert thread.options["name"] == "opengrader-job-worker"
    assert thread.options["daemon"] is True
    assert thread.started == 1
    assert worker._stop_event.is_set() is False


def test_stop_wakes_worker_and_uses_default_timeout(tmp_path: Path) -> None:
    class FakeThread:
        def __init__(self) -> None:
            self.joined_with: list[float | None] = []

        def join(self, timeout: float | None = None) -> None:
            self.joined_with.append(timeout)

    worker = JobWorker(RepositorySpy(), output_root=tmp_path)  # type: ignore[arg-type]
    thread = FakeThread()
    worker._thread = thread  # type: ignore[assignment]

    worker.stop()

    assert worker._stop_event.is_set() is True
    assert worker._wake_event.is_set() is True
    assert thread.joined_with == [5.0]

    worker._thread = None
    worker.stop()


@pytest.mark.parametrize(
    ("no_docker", "expected_runner_name"), [(True, "local"), (False, "docker")]
)
def test_run_once_propagates_the_complete_job_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    no_docker: bool,
    expected_runner_name: str,
) -> None:
    request = SimpleNamespace(
        assignment_file=tmp_path / "assignment.yaml",
        submissions_dir=tmp_path / "submissions",
        submission_patterns=["section-*"],
        no_docker=no_docker,
        workers=4,
        retries=2,
    )
    repository = RepositorySpy(SimpleNamespace(id="job-123", request=request))
    calls: dict[str, Any] = {}
    assignment = object()
    discovered = [object()]
    selected = [object()]
    runner = object()
    result = object()
    report_paths = (
        tmp_path / "out" / "results.json",
        tmp_path / "out" / "summary.md",
        tmp_path / "out" / "results.csv",
    )

    def load_assignment(path: Path) -> object:
        calls["assignment_path"] = path
        return assignment

    def discover_submissions(path: Path) -> list[object]:
        calls["submissions_path"] = path
        return discovered

    def select_submissions(
        submissions: list[object], patterns: list[str]
    ) -> list[object]:
        calls["selection"] = (submissions, patterns)
        return selected

    def runner_factory(value: bool) -> object:
        calls["no_docker"] = value
        return runner

    def grade_assignment(*args: object, **kwargs: object) -> object:
        calls["grade"] = (args, kwargs)
        return result

    def write_results(value: object, output_dir: Path) -> tuple[Path, Path, Path]:
        calls["write"] = (value, output_dir)
        return report_paths

    monkeypatch.setattr(worker_module, "load_assignment", load_assignment)
    monkeypatch.setattr(worker_module, "discover_submissions", discover_submissions)
    monkeypatch.setattr(worker_module, "select_submissions", select_submissions)
    monkeypatch.setattr(worker_module, "grade_assignment", grade_assignment)
    monkeypatch.setattr(worker_module, "write_results", write_results)
    worker = JobWorker(
        repository,  # type: ignore[arg-type]
        output_root=tmp_path / "reports",
        runner_factory=runner_factory,  # type: ignore[arg-type]
        worker_actor="worker:test",
    )

    assert worker.run_once() is True

    assert repository.claim_actors == ["worker:test"]
    assert calls["assignment_path"] == request.assignment_file
    assert calls["submissions_path"] == request.submissions_dir
    assert calls["selection"] == (discovered, ["section-*"])
    assert calls["no_docker"] is no_docker
    assert calls["grade"] == (
        (assignment, selected, runner, expected_runner_name),
        {"workers": 4, "retries": 2},
    )
    assert calls["write"] == (result, tmp_path / "reports" / "job-123")
    assert repository.completed == [
        {
            "job_id": "job-123",
            "result": result,
            "reports": {
                "json": str(report_paths[0].resolve()),
                "markdown": str(report_paths[1].resolve()),
                "csv": str(report_paths[2].resolve()),
            },
            "worker_actor": "worker:test",
        }
    ]
    assert repository.failed == []


def test_run_once_records_precise_failure_and_empty_queue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = SimpleNamespace(assignment_file=tmp_path / "missing.yaml")
    repository = RepositorySpy(SimpleNamespace(id="job-bad", request=request))
    worker = JobWorker(
        repository,  # type: ignore[arg-type]
        output_root=tmp_path,
        worker_actor="worker:test",
    )
    monkeypatch.setattr(
        worker_module,
        "load_assignment",
        lambda path: (_ for _ in ()).throw(RuntimeError(f"broken: {path.name}")),
    )

    assert worker.run_once() is True
    assert repository.failed == [
        {
            "job_id": "job-bad",
            "error": "RuntimeError: broken: missing.yaml",
            "worker_actor": "worker:test",
        }
    ]
    assert worker.run_once() is False
    assert repository.claim_actors == ["worker:test", "worker:test"]


def test_run_loop_waits_only_when_idle(tmp_path: Path) -> None:
    worker = JobWorker(
        RepositorySpy(),  # type: ignore[arg-type]
        output_root=tmp_path,
        poll_interval=0.125,
    )
    waits: list[float | None] = []
    clears: list[bool] = []

    def idle_once() -> bool:
        worker._stop_event.set()
        return False

    monkeypatch_event = SimpleNamespace(
        wait=lambda timeout=None: waits.append(timeout),
        clear=lambda: clears.append(True),
        set=lambda: None,
    )
    worker.run_once = idle_once  # type: ignore[method-assign]
    worker._wake_event = monkeypatch_event  # type: ignore[assignment]

    worker._run_loop()

    assert waits == [0.125]
    assert clears == [True]

    worker._stop_event.clear()
    waits.clear()
    clears.clear()

    def busy_once() -> bool:
        worker._stop_event.set()
        return True

    worker.run_once = busy_once  # type: ignore[method-assign]
    worker._run_loop()

    assert waits == []
    assert clears == []
