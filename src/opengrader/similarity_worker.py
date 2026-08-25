"""Managed in-process worker for durable similarity review jobs."""

from __future__ import annotations

import threading

from opengrader.similarity_repository import SimilarityRepository
from opengrader.similarity_service import SimilarityService


class SimilarityWorker:
    def __init__(self, repository: SimilarityRepository, service: SimilarityService, *, poll_interval: float = 0.25, worker_actor: str = "worker:similarity-local") -> None:
        if poll_interval <= 0:
            raise ValueError("poll_interval must be positive")
        self.repository = repository
        self.service = service
        self.poll_interval = poll_interval
        self.worker_actor = worker_actor
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="opengrader-similarity-worker", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        self._wake_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def notify(self) -> None:
        self._wake_event.set()

    def run_once(self) -> bool:
        job = self.repository.claim_next(worker_actor=self.worker_actor)
        if job is None:
            return False
        try:
            report = self.service.analyze(job)
            self.repository.complete(job.id, report=report, worker_actor=self.worker_actor)
        except Exception as exc:
            self.repository.fail(job.id, error=f"{type(exc).__name__}: {exc}", worker_actor=self.worker_actor)
        return True

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            if not self.run_once():
                self._wake_event.wait(self.poll_interval)
                self._wake_event.clear()
