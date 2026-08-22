from pathlib import Path

import pytest

from core.download import build_opts, ensure_writable, run
from core.queue import Job

SALIDA = Path("/descargas")
FFMPEG = "/ruta/ffmpeg.exe"


def _video(**extra):
    base = {
        "mode": "video",
        "video_format_id": "137",
        "audio_format_id": "251",
        "container": "mp4",
        "subtitle_lang": None,
        "subtitle_auto": False,
        "embed_subs": True,
        "keep_srt": True,
        "filesize_approx": None,
    }
    base.update(extra)
    return base


def test_une_video_y_audio_cuando_van_separados():
    opts = build_opts(_video(), FFMPEG, SALIDA)

    assert opts["format"] == "137+251"
    assert opts["merge_output_format"] == "mp4"


def test_usa_un_solo_formato_cuando_ya_trae_audio():
    opts = build_opts(_video(audio_format_id=None), FFMPEG, SALIDA)

    assert opts["format"] == "137"


def test_pasa_la_ruta_de_ffmpeg():
    opts = build_opts(_video(), FFMPEG, SALIDA)

    assert opts["ffmpeg_location"] == FFMPEG


def test_nunca_baja_playlists():
    assert build_opts(_video(), FFMPEG, SALIDA)["noplaylist"] is True


def test_modo_audio_extrae_y_convierte():
    opts = build_opts(
        {"mode": "audio", "audio_format": "mp3", "subtitle_lang": None},
        FFMPEG,
        SALIDA,
    )

    assert opts["format"] == "bestaudio/best"
    assert opts["postprocessors"][0]["key"] == "FFmpegExtractAudio"
    assert opts["postprocessors"][0]["preferredcodec"] == "mp3"


def test_subtitulos_manuales_piden_la_pista_correcta():
    opts = build_opts(_video(subtitle_lang="es"), FFMPEG, SALIDA)

    assert opts["subtitleslangs"] == ["es"]
    assert opts["subtitlesformat"] == "srt"
    assert opts["writesubtitles"] is True
    assert "writeautomaticsub" not in opts


def test_subtitulos_autogenerados_usan_la_otra_bandera():
    opts = build_opts(_video(subtitle_lang="pt", subtitle_auto=True), FFMPEG, SALIDA)

    assert opts["writeautomaticsub"] is True
    assert "writesubtitles" not in opts


def test_incrustar_conservando_el_srt():
    opts = build_opts(_video(subtitle_lang="es", embed_subs=True, keep_srt=True), FFMPEG, SALIDA)
    incrustar = next(p for p in opts["postprocessors"] if p["key"] == "FFmpegEmbedSubtitle")

    # already_have_subtitle=True es lo que evita que yt-dlp borre el .srt
    assert incrustar["already_have_subtitle"] is True


def test_incrustar_sin_conservar_el_srt():
    opts = build_opts(_video(subtitle_lang="es", embed_subs=True, keep_srt=False), FFMPEG, SALIDA)
    incrustar = next(p for p in opts["postprocessors"] if p["key"] == "FFmpegEmbedSubtitle")

    assert incrustar["already_have_subtitle"] is False


def test_sin_incrustar_no_hay_postprocesador():
    opts = build_opts(_video(subtitle_lang="es", embed_subs=False), FFMPEG, SALIDA)

    assert not any(p["key"] == "FFmpegEmbedSubtitle" for p in opts.get("postprocessors", []))


def test_sin_idioma_no_se_piden_subtitulos():
    opts = build_opts(_video(subtitle_lang=None), FFMPEG, SALIDA)

    assert "subtitleslangs" not in opts


def test_destino_valido_no_lanza(tmp_path):
    from collections import namedtuple

    Uso = namedtuple("Uso", "total used free")
    ensure_writable(tmp_path, needed_bytes=1000, usage=lambda p: Uso(100, 50, 50_000))


def test_destino_sin_espacio_lanza(tmp_path):
    from collections import namedtuple

    from core.download import DestinationError

    Uso = namedtuple("Uso", "total used free")
    with pytest.raises(DestinationError, match="espacio"):
        ensure_writable(tmp_path, needed_bytes=1_000_000, usage=lambda p: Uso(100, 99, 1000))


def test_destino_sin_permiso_de_escritura(tmp_path, monkeypatch):
    from core.download import DestinationError

    def sin_permiso(*args, **kwargs):
        raise PermissionError("acceso denegado")

    monkeypatch.setattr("core.download.tempfile.NamedTemporaryFile", sin_permiso)

    with pytest.raises(DestinationError, match="permiso"):
        ensure_writable(tmp_path)


def test_crea_el_directorio_si_no_existe(tmp_path):
    destino = tmp_path / "nueva" / "carpeta"

    ensure_writable(destino)

    assert destino.is_dir()


def test_run_verifica_el_destino_antes_de_descargar(tmp_path):
    from core.download import DestinationError

    class NuncaLlamado:
        def __init__(self, opts):
            raise AssertionError("no debería construirse el descargador")

    job = Job(id=1, url="https://ejemplo.com/a", title="x", options=_video())
    archivo = tmp_path / "soy-un-archivo"
    archivo.write_text("no soy carpeta")

    with pytest.raises(DestinationError):
        run(job, lambda p, v: None, FFMPEG, archivo, ydl_factory=NuncaLlamado)


def test_run_reporta_progreso_y_devuelve_la_ruta(tmp_path):
    reportes = []

    class YdlFalso:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def extract_info(self, url, download=True):
            hook = self.opts["progress_hooks"][0]
            hook({"status": "downloading", "downloaded_bytes": 50, "total_bytes": 100, "_speed_str": " 2MiB/s "})
            hook({"status": "finished", "filename": str(tmp_path / "video.mp4")})
            return {"title": "video"}

    job = Job(id=1, url="https://ejemplo.com/a", title="video", options=_video())

    ruta = run(
        job,
        on_progress=lambda pct, vel: reportes.append((pct, vel)),
        ffmpeg_path=FFMPEG,
        outdir=tmp_path,
        ydl_factory=YdlFalso,
    )

    assert reportes == [(50.0, "2MiB/s")]
    assert ruta == str(tmp_path / "video.mp4")


def test_run_no_divide_por_cero_sin_tamano_total(tmp_path):
    reportes = []

    class YdlFalso:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def extract_info(self, url, download=True):
            hook = self.opts["progress_hooks"][0]
            hook({"status": "downloading", "downloaded_bytes": 50, "_speed_str": ""})
            hook({"status": "finished", "filename": str(tmp_path / "x.mp4")})
            return {}

    job = Job(id=1, url="https://ejemplo.com/a", title="x", options=_video())

    run(job, lambda p, v: reportes.append(p), FFMPEG, tmp_path, ydl_factory=YdlFalso)

    assert reportes == [0.0]
