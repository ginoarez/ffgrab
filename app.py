from __future__ import annotations

import dataclasses
import json
import threading
from pathlib import Path

from core import deps
from core import download as download_mod
from core import probe as probe_mod
from core.queue import DownloadQueue, Job, JobState

RAIZ = Path(__file__).resolve().parent
PAGINA = RAIZ / "web" / "index.html"


def _job_a_dict(job: Job) -> dict:
    return {
        "id": job.id,
        "url": job.url,
        "title": job.title,
        "state": job.state.value,
        "progress": float(job.progress),
        "speed": job.speed,
        "error": job.error,
        "output_path": job.output_path,
    }


class Api:
    """Todo lo que el JavaScript puede llamar.

    Ningún método lanza excepciones: los errores viajan como {"ok": False}.
    """

    def __init__(self, outdir: Path | None = None):
        self.window = None
        self.outdir = Path(outdir) if outdir else Path.home() / "Downloads"
        self.queue = DownloadQueue(runner=self._ejecutar, on_change=self._empujar)
        self._despierta = threading.Event()
        self._worker: threading.Thread | None = None

    # ---- dependencias ----

    def deps_status(self) -> dict:
        try:
            estado = deps.ffmpeg_status()
            return {
                "ok": True,
                "ffmpeg": estado.state.value,
                "path": str(estado.path) if estado.path else None,
                "version": estado.version,
                "ytdlp_update": deps.ytdlp_update_available(),
            }
        except Exception as error:
            return {"ok": False, "error": str(error)}

    def install_ffmpeg(self) -> dict:
        try:
            ruta = deps.install_ffmpeg(on_progress=self._empujar_instalacion)
            return {"ok": True, "path": str(ruta)}
        except Exception as error:
            return {"ok": False, "error": str(error)}

    # ---- consulta ----

    def probe(self, url: str) -> dict:
        try:
            info = probe_mod.probe(url)
        except Exception as error:
            return {"ok": False, "error": str(error)}

        return {
            "ok": True,
            "id": info.id,
            "title": info.title,
            "duration": info.duration,
            "thumbnail_url": info.thumbnail_url,
            "uploader": info.uploader,
            "qualities": [dataclasses.asdict(q) for q in info.qualities],
            "subtitles": [dataclasses.asdict(s) for s in info.subtitles],
        }

    # ---- cola ----

    def enqueue(self, payload: dict) -> dict:
        try:
            job = self.queue.enqueue(
                payload["url"], payload.get("title") or payload["url"], payload.get("options") or {}
            )
        except Exception as error:
            return {"ok": False, "error": str(error)}
        return {"ok": True, "job": _job_a_dict(job)}

    def jobs(self) -> list[dict]:
        # A diferencia del resto: el JavaScript itera esta lista directamente,
        # así que un {"ok": False} rompería esa iteración. Una lista vacía es
        # la respuesta segura que nunca deja de ser iterable.
        try:
            return [_job_a_dict(j) for j in self.queue.jobs()]
        except Exception:
            return []

    def cancel(self, job_id: int) -> dict:
        try:
            self.queue.cancel(int(job_id))
        except Exception as error:
            return {"ok": False, "error": str(error)}
        return {"ok": True}

    def current_folder(self) -> str:
        return str(self.outdir)

    def choose_folder(self) -> str | None:
        if self.window is None:
            return None
        try:
            import webview

            elegido = self.window.create_file_dialog(webview.FOLDER_DIALOG)
            if elegido:
                self.outdir = Path(elegido[0])
                return str(self.outdir)
            return None
        except Exception:
            return None

    # ---- interno ----

    def _ejecutar(self, job: Job, on_progress) -> str:
        estado = deps.ffmpeg_status()
        if estado.path is None:
            raise RuntimeError("ffmpeg no está disponible.")
        self.outdir.mkdir(parents=True, exist_ok=True)
        return download_mod.run(job, on_progress, str(estado.path), self.outdir)

    def _empujar(self, job: Job) -> None:
        self._evaluar("window.onJobChange", _job_a_dict(job))

    def _empujar_instalacion(self, porcentaje: float) -> None:
        self._evaluar("window.onFfmpegProgress", porcentaje)

    def _evaluar(self, funcion: str, dato) -> None:
        if self.window is None:
            return
        try:
            self.window.evaluate_js(f"{funcion}({json.dumps(dato)})")
        except Exception:
            pass  # la ventana puede haberse cerrado a mitad de una descarga

    def _asegurar_worker(self) -> None:
        if self._worker and self._worker.is_alive():
            self._despierta.set()
            return
        self._worker = threading.Thread(target=self._bombear, daemon=True)
        self._worker.start()

    def _bombear(self) -> None:
        while True:
            if not self._bombear_paso():
                self._despierta.clear()
                self._despierta.wait(timeout=1.0)

    def _bombear_paso(self) -> bool:
        """Un pulso del bombeo: procesa un trabajo pendiente si lo hay.

        Nunca deja escapar una excepción. `queue.run_next()` invoca el
        callback on_change directamente, sin protegerlo: si ese aviso revienta
        (por ejemplo, al serializar un job raro), la excepción subiría hasta
        acá y mataría el único hilo trabajador para siempre, sin ningún
        síntoma visible en la ventana. Perder un aviso es aceptable; perder el
        hilo no.
        """
        try:
            return self.queue.run_next() is not None
        except Exception:
            return True  # hubo un trabajo (aunque su aviso fallara); seguimos


def main() -> None:
    import webview

    api = Api()
    ventana = webview.create_window(
        "FFGrab", str(PAGINA), js_api=api, width=1000, height=640, min_size=(860, 560)
    )
    api.window = ventana
    # Un único hilo persiste durante toda la vida de la app y va tomando los
    # trabajos pendientes. Arrancarlo aquí (y no dentro de cada enqueue())
    # evita que un enqueue() en caliente compita con quien lo llamó por leer
    # el estado del job recién creado.
    api._asegurar_worker()
    webview.start()


if __name__ == "__main__":
    main()
