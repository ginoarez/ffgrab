from __future__ import annotations

import itertools
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class JobState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobCancelled(Exception):
    """Se pidió cancelar el trabajo que estaba corriendo."""


@dataclass
class Job:
    id: int
    url: str
    title: str
    options: dict = field(default_factory=dict)
    state: JobState = JobState.PENDING
    progress: float = 0.0
    speed: str = ""
    error: str | None = None
    output_path: str | None = None


class DownloadQueue:
    """Cola secuencial. Una descarga a la vez, siempre.

    `run_next()` procesa un trabajo y devuelve. No arranca hilos por su cuenta:
    quien la usa decide si la bombea desde un hilo o desde un test.
    """

    def __init__(
        self,
        runner: Callable[[Job, Callable[[float, str], None]], str] | None,
        on_change: Callable[[Job], None] | None = None,
    ):
        self._runner = runner
        self._on_change = on_change or (lambda job: None)
        self._jobs: list[Job] = []
        self._ids = itertools.count(1)
        self._cancelados: set[int] = set()
        self._lock = threading.RLock()

    def enqueue(self, url: str, title: str, options: dict) -> Job:
        with self._lock:
            job = Job(id=next(self._ids), url=url, title=title, options=options)
            self._jobs.append(job)
        self._on_change(job)
        return job

    def jobs(self) -> list[Job]:
        with self._lock:
            return list(self._jobs)

    def cancel(self, job_id: int) -> None:
        with self._lock:
            job = next((j for j in self._jobs if j.id == job_id), None)
            if job is None:
                return
            self._cancelados.add(job_id)
            if job.state is not JobState.PENDING:
                return  # si corre, lo aborta el callback de progreso
            job.state = JobState.CANCELLED
        self._on_change(job)

    def run_next(self) -> Job | None:
        with self._lock:
            job = next((j for j in self._jobs if j.state is JobState.PENDING), None)
            if job is None:
                return None
            job.state = JobState.RUNNING
        self._on_change(job)

        try:
            salida = self._runner(job, self._progreso_de(job))
        except JobCancelled:
            with self._lock:
                job.state = JobState.CANCELLED
        except Exception as error:
            with self._lock:
                job.state = JobState.FAILED
                job.error = str(error)
        else:
            with self._lock:
                job.state = JobState.DONE
                job.progress = 100.0
                job.output_path = str(salida)

        self._on_change(job)
        return job

    def _progreso_de(self, job: Job) -> Callable[[float, str], None]:
        def reportar(porcentaje: float, velocidad: str = "") -> None:
            with self._lock:
                if job.id in self._cancelados:
                    raise JobCancelled()
                job.progress = porcentaje
                job.speed = velocidad
            self._on_change(job)

        return reportar
