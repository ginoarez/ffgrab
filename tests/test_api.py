from pathlib import Path

import pytest

from app import Api
from core.deps import FFmpegState, FFmpegStatus
from tests.fixtures.info_dicts import VIDEO_CON_SUBTITULOS


@pytest.fixture
def api(tmp_path):
    instancia = Api(outdir=tmp_path)
    instancia.window = None
    return instancia


def test_deps_status_serializa_a_json(api, monkeypatch):
    monkeypatch.setattr(
        "app.deps.ffmpeg_status",
        lambda: FFmpegStatus(FFmpegState.FOUND, Path("/x/ffmpeg.exe"), "ffmpeg version 8.1.1"),
    )
    monkeypatch.setattr("app.deps.ytdlp_update_available", lambda: None)

    resultado = api.deps_status()

    assert resultado["ok"] is True
    assert resultado["ffmpeg"] == "found"
    assert resultado["version"] == "ffmpeg version 8.1.1"
    assert resultado["ytdlp_update"] is None


def test_deps_status_informa_ffmpeg_ausente(api, monkeypatch):
    monkeypatch.setattr("app.deps.ffmpeg_status", lambda: FFmpegStatus(FFmpegState.MISSING))
    monkeypatch.setattr("app.deps.ytdlp_update_available", lambda: "2026.8.19")

    resultado = api.deps_status()

    assert resultado["ffmpeg"] == "missing"
    assert resultado["ytdlp_update"] == "2026.8.19"


def test_probe_devuelve_diccionarios_planos(api, monkeypatch):
    from core.formats import normalize

    monkeypatch.setattr("app.probe_mod.probe", lambda url: normalize(VIDEO_CON_SUBTITULOS))

    resultado = api.probe("https://ejemplo.com/v/x")

    assert resultado["ok"] is True
    assert resultado["title"] == "Charla con subtitulos"
    assert isinstance(resultado["qualities"], list)
    assert isinstance(resultado["qualities"][0], dict)
    assert resultado["qualities"][0]["label"] == "1080p"
    assert resultado["subtitles"][0]["is_auto"] is False


def test_probe_convierte_errores_en_respuesta(api, monkeypatch):
    from core.probe import UnsupportedSite

    def explota(url):
        raise UnsupportedSite("Ese enlace no pertenece a ningún sitio soportado.")

    monkeypatch.setattr("app.probe_mod.probe", explota)

    resultado = api.probe("https://ejemplo.com")

    assert resultado["ok"] is False
    assert "soportado" in resultado["error"]


def test_enqueue_registra_el_trabajo(api):
    resultado = api.enqueue(
        {"url": "https://ejemplo.com/a", "title": "Un video", "options": {"mode": "video"}}
    )

    assert resultado["ok"] is True
    assert resultado["job"]["id"] == 1
    assert resultado["job"]["state"] == "pending"


def test_jobs_lista_todo_en_json(api):
    api.enqueue({"url": "https://ejemplo.com/a", "title": "A", "options": {}})
    api.enqueue({"url": "https://ejemplo.com/b", "title": "B", "options": {}})

    lista = api.jobs()

    assert [j["title"] for j in lista] == ["A", "B"]
    assert all(isinstance(j["progress"], float) for j in lista)


def test_cancel_marca_el_trabajo(api):
    job = api.enqueue({"url": "https://ejemplo.com/a", "title": "A", "options": {}})["job"]

    resultado = api.cancel(job["id"])

    assert resultado["ok"] is True
    assert api.jobs()[0]["state"] == "cancelled"


def test_bombear_paso_sobrevive_a_un_fallo_en_on_change(api, monkeypatch):
    """Si el aviso on_change revienta para un trabajo, el bombeo no debe
    morir: el siguiente trabajo pendiente tiene que seguir procesándose.

    Se prueba de forma sincrónica, llamando a `_bombear_paso()` directamente
    en vez de levantar un hilo real: así se comprueba que el propio paso
    nunca deja escapar la excepción (si la dejara escapar, esta prueba
    fallaría con un error, no con un assert) y que el estado interno queda
    en condiciones de seguir avanzando después, que es exactamente lo que
    `_bombear()` hace en su bucle infinito.
    """
    monkeypatch.setattr(
        "app.deps.ffmpeg_status",
        lambda: FFmpegStatus(FFmpegState.FOUND, Path("/x/ffmpeg.exe"), "ffmpeg version 8.1.1"),
    )
    monkeypatch.setattr("app.download_mod.run", lambda *args, **kwargs: "/salida/video.mp4")

    llamadas = {"n": 0}
    evaluar_original = api._evaluar

    def evaluar_que_revienta_la_primera_vez(funcion, dato):
        llamadas["n"] += 1
        if llamadas["n"] == 1:
            raise RuntimeError("fallo simulado en el aviso a la ventana")
        return evaluar_original(funcion, dato)

    # Se encolan ANTES de parchear _evaluar: DownloadQueue.enqueue() también
    # dispara on_change, y no queremos que ese aviso (al registrar el job)
    # consuma el "revienta una vez" que buscamos activar recién en el bombeo.
    trabajo_a = api.enqueue({"url": "https://ejemplo.com/a", "title": "A", "options": {}})["job"]
    trabajo_b = api.enqueue({"url": "https://ejemplo.com/b", "title": "B", "options": {}})["job"]

    monkeypatch.setattr(api, "_evaluar", evaluar_que_revienta_la_primera_vez)

    # Primer pulso: toma A, su aviso de "paso a running" revienta. El paso no
    # debe propagar esa excepción hacia afuera.
    assert api._bombear_paso() is True

    # Segundo pulso: A quedó atascado en "running" (la excepción interrumpió
    # su procesamiento antes de llegar al runner), así que ahora le toca a B,
    # cuyo aviso ya no revienta.
    assert api._bombear_paso() is True

    estados = {j["id"]: j["state"] for j in api.jobs()}
    assert estados[trabajo_a["id"]] == "running"
    assert estados[trabajo_b["id"]] == "done"

    # No debería quedar nada más pendiente: el hilo seguiría vivo esperando.
    assert api._bombear_paso() is False


def test_jobs_devuelve_lista_vacia_si_algo_falla(api, monkeypatch):
    def explota():
        raise RuntimeError("fallo simulado leyendo la cola")

    monkeypatch.setattr(api.queue, "jobs", explota)

    assert api.jobs() == []


def test_choose_folder_devuelve_none_si_la_ventana_falla(api):
    class VentanaQueFalla:
        def create_file_dialog(self, *args, **kwargs):
            raise RuntimeError("fallo simulado en el diálogo nativo")

    api.window = VentanaQueFalla()

    assert api.choose_folder() is None
