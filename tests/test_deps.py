from pathlib import Path

from core.deps import FFmpegState, ffmpeg_status


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


def test_cae_al_path_del_sistema_si_no_hay_empaquetado(tmp_path, monkeypatch):
    del_sistema = tmp_path / "sistema" / "ffmpeg"
    del_sistema.parent.mkdir()
    del_sistema.write_text("binario falso")
    monkeypatch.setattr("core.deps.shutil.which", lambda _: str(del_sistema))

    status = ffmpeg_status(bundled_dir=tmp_path / "vacio", verifier=lambda p: "ffmpeg version 7.0")

    assert status.state is FFmpegState.FOUND
    assert status.path == del_sistema
