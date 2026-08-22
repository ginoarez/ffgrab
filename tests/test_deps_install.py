import zipfile
from pathlib import Path

import pytest

from core.deps import install_ffmpeg, ytdlp_update_available


def _zip_falso(destino: Path) -> Path:
    """Imita el zip de gyan.dev: el binario vive en un subdirectorio."""
    archivo = destino / "ffmpeg.zip"
    with zipfile.ZipFile(archivo, "w") as z:
        z.writestr("ffmpeg-8.1.1-full_build/bin/ffmpeg.exe", "binario falso")
        z.writestr("ffmpeg-8.1.1-full_build/bin/ffprobe.exe", "otro binario")
        z.writestr("ffmpeg-8.1.1-full_build/LICENSE", "texto")
    return archivo


def _descargador_falso(origen: Path):
    """Imita _descargar: mueve un zip ya preparado al destino y reporta 100%."""

    def descargar(url, hacia, on_progress):
        hacia.parent.mkdir(parents=True, exist_ok=True)
        hacia.write_bytes(origen.read_bytes())
        on_progress(100.0)
        return hacia

    return descargar


def test_extrae_ffmpeg_del_zip_ignorando_subdirectorios(tmp_path):
    origen = _zip_falso(tmp_path)
    destino = tmp_path / "bin"
    progreso = []

    resultado = install_ffmpeg(
        on_progress=progreso.append,
        dest_dir=destino,
        downloader=_descargador_falso(origen),
    )

    assert resultado == destino / "ffmpeg.exe"
    assert resultado.exists()
    assert (destino / "ffprobe.exe").exists()
    assert progreso == [100.0]


def test_borra_el_zip_despues_de_extraer(tmp_path):
    origen = _zip_falso(tmp_path)
    destino = tmp_path / "bin"

    install_ffmpeg(
        on_progress=lambda _: None,
        dest_dir=destino,
        downloader=_descargador_falso(origen),
    )

    assert list(destino.glob("*.zip")) == []


def test_falla_si_el_zip_no_trae_ffmpeg(tmp_path):
    vacio = tmp_path / "vacio.zip"
    with zipfile.ZipFile(vacio, "w") as z:
        z.writestr("readme.txt", "nada util")

    with pytest.raises(RuntimeError, match="no contenía ffmpeg"):
        install_ffmpeg(
            on_progress=lambda _: None,
            dest_dir=tmp_path / "bin",
            downloader=_descargador_falso(vacio),
        )


def test_avisa_cuando_hay_version_nueva():
    assert ytdlp_update_available(installed="2026.1.1", fetcher=lambda: "2026.8.19") == "2026.8.19"


def test_no_avisa_si_esta_al_dia():
    assert ytdlp_update_available(installed="2026.8.19", fetcher=lambda: "2026.8.19") is None


def test_no_avisa_si_no_se_puede_consultar():
    def explota():
        raise OSError("sin red")

    assert ytdlp_update_available(installed="2026.1.1", fetcher=explota) is None


def test_limpia_zip_si_descarga_falla(tmp_path):
    def descargador_roto(url, hacia, on_progress):
        hacia.parent.mkdir(parents=True, exist_ok=True)
        hacia.write_bytes(b"contenido parcial")
        raise OSError("conexión perdida")

    destino = tmp_path / "bin"

    with pytest.raises(OSError, match="conexión perdida"):
        install_ffmpeg(
            on_progress=lambda _: None,
            dest_dir=destino,
            downloader=descargador_roto,
        )

    assert list(destino.glob("*.zip")) == []
