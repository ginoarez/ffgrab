import pytest

from core.probe import ProbeError, UnsupportedSite, VideoUnavailable, probe
from tests.fixtures.info_dicts import VIDEO_NORMAL


class YdlFalso:
    """Imita el gestor de contexto de YoutubeDL."""

    def __init__(self, resultado=None, error=None):
        self._resultado = resultado
        self._error = error
        self.url_recibida = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def extract_info(self, url, download):
        self.url_recibida = url
        if self._error:
            raise self._error
        return self._resultado


def test_devuelve_la_info_normalizada():
    falso = YdlFalso(resultado=VIDEO_NORMAL)

    info = probe("https://ejemplo.com/v/abc123", ydl_factory=lambda: falso)

    assert info.title == "Un video de prueba"
    assert len(info.qualities) == 3
    assert falso.url_recibida == "https://ejemplo.com/v/abc123"


def test_nunca_descarga():
    registro = {}

    class Espia(YdlFalso):
        def extract_info(self, url, download):
            registro["download"] = download
            return VIDEO_NORMAL

    probe("https://ejemplo.com/v/abc", ydl_factory=lambda: Espia())

    assert registro["download"] is False


def test_sitio_no_soportado():
    from yt_dlp.utils import DownloadError

    falso = YdlFalso(error=DownloadError("ERROR: Unsupported URL: https://ejemplo.com"))

    with pytest.raises(UnsupportedSite):
        probe("https://ejemplo.com", ydl_factory=lambda: falso)


def test_video_privado():
    from yt_dlp.utils import DownloadError

    falso = YdlFalso(error=DownloadError("ERROR: Private video. Sign in if you've been granted access"))

    with pytest.raises(VideoUnavailable):
        probe("https://ejemplo.com/v/x", ydl_factory=lambda: falso)


def test_video_eliminado():
    from yt_dlp.utils import DownloadError

    falso = YdlFalso(error=DownloadError("ERROR: Video unavailable. This video has been removed"))

    with pytest.raises(VideoUnavailable):
        probe("https://ejemplo.com/v/x", ydl_factory=lambda: falso)


def test_error_desconocido_conserva_el_mensaje():
    from yt_dlp.utils import DownloadError

    falso = YdlFalso(error=DownloadError("ERROR: algo raro pasó"))

    with pytest.raises(ProbeError, match="algo raro pasó") as excinfo:
        probe("https://ejemplo.com/v/x", ydl_factory=lambda: falso)

    assert type(excinfo.value) is ProbeError


def test_video_privado_formato_youtube():
    from yt_dlp.utils import DownloadError

    falso = YdlFalso(error=DownloadError("ERROR: Video dQw4w9WgXcQ is private"))

    with pytest.raises(VideoUnavailable):
        probe("https://ejemplo.com/v/x", ydl_factory=lambda: falso)


def test_video_bloqueado_geograficamente():
    from yt_dlp.utils import DownloadError

    falso = YdlFalso(error=DownloadError("ERROR: The uploader has not made this video available in your country"))

    with pytest.raises(VideoUnavailable):
        probe("https://ejemplo.com/v/x", ydl_factory=lambda: falso)


def test_respuesta_vacia_es_no_disponible():
    falso = YdlFalso(resultado=None)

    with pytest.raises(VideoUnavailable):
        probe("https://ejemplo.com/v/x", ydl_factory=lambda: falso)


def test_la_consulta_nunca_expande_una_lista():
    """Un enlace con ?list= debe resolver el video, no la lista entera.

    Sin esto, un enlace de radio de YouTube hace que yt-dlp extraiga decenas
    de videos antes de responder, y la interfaz parece colgada.
    """
    from core.probe import _OPCIONES

    assert _OPCIONES["noplaylist"] is True
