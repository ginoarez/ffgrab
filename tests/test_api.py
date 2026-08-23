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
