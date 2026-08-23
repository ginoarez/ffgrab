from pathlib import Path

from core.deps import FFmpegState, _verify, ffmpeg_status


def test_encuentra_ffmpeg_empaquetado(tmp_path):
    exe = tmp_path / "ffmpeg.exe"
    exe.write_text("binario falso")

    status = ffmpeg_status(bundled_dir=tmp_path, verifier=lambda p: "ffmpeg version 8.1.1")

    assert status.state is FFmpegState.FOUND
    assert status.path == exe
    assert status.version == "ffmpeg version 8.1.1"


def test_reporta_missing_si_no_hay_nada(tmp_path, monkeypatch):
    monkeypatch.setattr("core.deps.shutil.which", lambda _: None)

    status = ffmpeg_status(bundled_dir=tmp_path, verifier=lambda p: "no debería llamarse")

    assert status.state is FFmpegState.MISSING
    assert status.path is None


def test_binario_presente_pero_corrupto_es_broken(tmp_path, monkeypatch):
    monkeypatch.setattr("core.deps.shutil.which", lambda _: None)
    (tmp_path / "ffmpeg.exe").write_text("basura")

    status = ffmpeg_status(bundled_dir=tmp_path, verifier=lambda p: None)

    assert status.state is FFmpegState.BROKEN


def test_verify_de_una_ruta_inexistente_devuelve_none(tmp_path):
    """_verify() es el unico codigo con subprocess real de la produccion,
    y hasta ahora los cuatro tests de este archivo lo evitaban inyectando
    un verifier falso. Un binario que no existe dispara OSError
    (FileNotFoundError) al lanzar el proceso: esa rama debe devolver None,
    no dejar escapar la excepcion."""
    ruta_inexistente = tmp_path / "no-existe.exe"

    assert _verify(ruta_inexistente) is None


def test_verify_de_un_comando_con_codigo_no_cero_devuelve_none(tmp_path):
    """Un binario que existe y corre, pero devuelve un codigo de salida
    distinto de cero, tampoco cuenta como version valida. No hace falta
    un ffmpeg real: un .bat que sale con returncode 1 basta para
    ejercitar la misma rama (result.returncode != 0)."""
    fake = tmp_path / "fake.bat"
    fake.write_text("@echo off\r\nexit /b 1\r\n")

    assert _verify(fake) is None


def test_cae_al_path_del_sistema_si_no_hay_empaquetado(tmp_path, monkeypatch):
    del_sistema = tmp_path / "sistema" / "ffmpeg"
    del_sistema.parent.mkdir()
    del_sistema.write_text("binario falso")
    monkeypatch.setattr("core.deps.shutil.which", lambda _: str(del_sistema))

    status = ffmpeg_status(bundled_dir=tmp_path / "vacio", verifier=lambda p: "ffmpeg version 7.0")

    assert status.state is FFmpegState.FOUND
    assert status.path == del_sistema
