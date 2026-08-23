from __future__ import annotations

import dataclasses
import json
import threading
import time
from pathlib import Path

from core import deps
from core import download as download_mod
from core import probe as probe_mod
from core.queue import DownloadQueue, Job

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
        self._window = None
        self._outdir = Path(outdir) if outdir else Path.home() / "Downloads"
        self._queue = DownloadQueue(runner=self._ejecutar, on_change=self._empujar)
        self._cookies: dict = {}
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
            }
        except Exception as error:
            return {"ok": False, "error": str(error)}

    def ytdlp_update(self) -> dict:
        """Separado de deps_status a propósito: consulta PyPI con un timeout
        de 10s, y deps_status es lo que la compuerta espera para mostrar la
        app. Bombeada junto a deps_status, un PyPI lento o inalcanzable
        retrasaba la compuerta ~10s sin ninguna razón relacionada con
        ffmpeg. Se llama aparte, después de que la compuerta ya se abrió.
        """
        try:
            return {"ok": True, "update": deps.ytdlp_update_available()}
        except Exception as error:
            return {"ok": False, "error": str(error)}

    def install_ffmpeg(self) -> dict:
        try:
            ruta = deps.install_ffmpeg(on_progress=self._empujar_instalacion)
            return {"ok": True, "path": str(ruta)}
        except Exception as error:
            return {"ok": False, "error": str(error)}

    # ---- consulta ----

    def set_cookies(self, origen: str) -> dict:
        """Elige de donde sacar la sesion para sitios que exigen login.

        Muchos sitios responden a una consulta anonima con una verificacion
        anti-bot. Leer las cookies del navegador donde ya iniciaste sesion es
        el mecanismo que soporta yt-dlp para saltarla.
        """
        try:
            if not origen or origen == "ninguno":
                self._cookies = {}
            elif origen.startswith("archivo:"):
                self._cookies = {"cookiefile": origen.split(":", 1)[1]}
            else:
                self._cookies = {"cookiesfrombrowser": (origen,)}
        except Exception as error:
            return {"ok": False, "error": str(error)}
        return {"ok": True, "origen": origen or "ninguno"}

    def probe(self, url: str) -> dict:
        try:
            info = probe_mod.probe(url, cookies=self._cookies)
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
            job = self._queue.enqueue(
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
            return [_job_a_dict(j) for j in self._queue.jobs()]
        except Exception:
            return []

    def cancel(self, job_id: int) -> dict:
        try:
            self._queue.cancel(int(job_id))
        except Exception as error:
            return {"ok": False, "error": str(error)}
        return {"ok": True}

    def retry(self, job_id: int) -> dict:
        try:
            self._queue.retry(int(job_id))
        except Exception as error:
            return {"ok": False, "error": str(error)}
        return {"ok": True}

    def current_folder(self) -> str:
        return str(self._outdir)

    def choose_folder(self) -> str | None:
        if self._window is None:
            return None
        try:
            import webview

            elegido = self._window.create_file_dialog(webview.FOLDER_DIALOG)
            if elegido:
                self._outdir = Path(elegido[0])
                return str(self._outdir)
            return None
        except Exception:
            return None

    def choose_cookie_file(self) -> str | None:
        """Abre un dialogo nativo para elegir un cookies.txt exportado.

        Sigue exactamente la convencion de choose_folder: nunca lanza, y
        devuelve una ruta desnuda (o None), no un sobre {ok: ...}.
        """
        if self._window is None:
            return None
        try:
            import webview

            elegido = self._window.create_file_dialog(webview.OPEN_DIALOG)
            if elegido:
                return str(elegido[0])
            return None
        except Exception:
            return None

    # ---- interno ----

    def _ejecutar(self, job: Job, on_progress) -> str:
        estado = deps.ffmpeg_status()
        if estado.path is None:
            raise RuntimeError("ffmpeg no está disponible.")
        self._outdir.mkdir(parents=True, exist_ok=True)
        # La descarga necesita la misma sesion que la consulta.
        job.options["cookies"] = self._cookies
        return download_mod.run(job, on_progress, str(estado.path), self._outdir)

    def _empujar(self, job: Job) -> None:
        self._evaluar("window.onJobChange", _job_a_dict(job))

    def _empujar_instalacion(self, porcentaje: float) -> None:
        self._evaluar("window.onFfmpegProgress", porcentaje)

    def _evaluar(self, funcion: str, dato) -> None:
        if self._window is None:
            return
        try:
            self._window.evaluate_js(f"{funcion}({json.dumps(dato)})")
        except Exception:
            pass  # la ventana puede haberse cerrado a mitad de una descarga

    def _asegurar_worker(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._worker = threading.Thread(target=self._bombear, daemon=True)
        self._worker.start()

    def _bombear(self) -> None:
        while True:
            if not self._bombear_paso():
                time.sleep(1.0)

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
            return self._queue.run_next() is not None
        except Exception:
            return True  # hubo un trabajo (aunque su aviso fallara); seguimos


def _usar_certificados_del_sistema() -> None:
    """Hace que Python valide TLS con el almacen de certificados de Windows.

    Python solo confia en su propio paquete de certificados publicos. Cuando
    un antivirus o un proxy corporativo inspecciona HTTPS, instala su raiz en
    el almacen del sistema —que Windows si usa y Python no—, y toda conexion
    falla con CERTIFICATE_VERIFY_FAILED aunque el navegador funcione. Sin
    esto, yt-dlp no puede alcanzar ningun sitio en esas maquinas.
    """
    try:
        import truststore

        truststore.inject_into_ssl()
    except Exception:
        pass  # sin truststore se usa el comportamiento por defecto


def main() -> None:
    import webview

    _usar_certificados_del_sistema()

    api = Api()
    ventana = webview.create_window(
        "FFGrab", str(PAGINA), js_api=api, width=1000, height=640, min_size=(860, 560)
    )
    api._window = ventana
    # Un único hilo persiste durante toda la vida de la app y va tomando los
    # trabajos pendientes. Arrancarlo aquí (y no dentro de cada enqueue())
    # evita que un enqueue() en caliente compita con quien lo llamó por leer
    # el estado del job recién creado.
    api._asegurar_worker()
    webview.start()


if __name__ == "__main__":
    main()
