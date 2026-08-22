from core.formats import normalize
from tests.fixtures.info_dicts import (
    FORMATOS_ROTOS,
    SOLO_AUDIO,
    VIDEO_4K_60FPS,
    VIDEO_MISMO_CODEC_DISTINTO_BITRATE,
    VIDEO_NORMAL,
    VIDEO_SIN_AUDIO_EMPAREJABLE,
)


def test_copia_los_metadatos_basicos():
    info = normalize(VIDEO_NORMAL)

    assert info.id == "abc123"
    assert info.title == "Un video de prueba"
    assert info.duration == 213
    assert info.thumbnail_url == "https://ejemplo.com/thumb.jpg"
    assert info.uploader == "Canal de prueba"


def test_colapsa_a_una_opcion_por_altura_ordenada_de_mayor_a_menor():
    info = normalize(VIDEO_NORMAL)

    assert [q.height for q in info.qualities] == [1080, 720, 360]


def test_prefiere_h264_sobre_vp9_a_la_misma_altura():
    info = normalize(VIDEO_NORMAL)
    mil_ochenta = next(q for q in info.qualities if q.height == 1080)

    assert mil_ochenta.video_format_id == "137"


def test_empareja_el_mejor_audio_y_marca_que_hay_que_unir():
    info = normalize(VIDEO_NORMAL)
    mil_ochenta = next(q for q in info.qualities if q.height == 1080)

    assert mil_ochenta.audio_format_id == "251"
    assert mil_ochenta.needs_merge is True


def test_formato_con_audio_propio_no_necesita_union():
    info = normalize(VIDEO_NORMAL)
    trescientos_sesenta = next(q for q in info.qualities if q.height == 360)

    assert trescientos_sesenta.needs_merge is False
    assert trescientos_sesenta.audio_format_id is None


def test_la_etiqueta_incluye_los_fps_solo_si_superan_30():
    normal = normalize(VIDEO_NORMAL)
    alto = normalize(VIDEO_4K_60FPS)

    assert next(q for q in normal.qualities if q.height == 1080).label == "1080p"
    assert next(q for q in alto.qualities if q.height == 2160).label == "2160p60"


def test_prefiere_vp9_sobre_av1_cuando_no_hay_h264():
    info = normalize(VIDEO_4K_60FPS)
    cuatro_k = next(q for q in info.qualities if q.height == 2160)

    assert cuatro_k.video_format_id == "315"


def test_un_video_solo_audio_no_ofrece_calidades():
    info = normalize(SOLO_AUDIO)

    assert info.qualities == ()


def test_descarta_formatos_sin_altura_o_sin_codec():
    info = normalize(FORMATOS_ROTOS)

    assert [q.video_format_id for q in info.qualities] == ["137"]


def test_descarta_alturas_sin_audio_emparejable():
    info = normalize(VIDEO_SIN_AUDIO_EMPAREJABLE)

    assert info.qualities == ()


def test_elige_mayor_tbr_cuando_el_codec_es_igual():
    """Verifica que el tiebreak por tbr funciona cuando dos formatos tienen el mismo codec."""
    info = normalize(VIDEO_MISMO_CODEC_DISTINTO_BITRATE)
    setecientos_veinte = next(q for q in info.qualities if q.height == 720)

    assert setecientos_veinte.video_format_id == "720p-high"


def test_filesize_approx_se_copia_correctamente():
    """Verifica que el tamaño aproximado del archivo se copia desde el formato original."""
    info = normalize(VIDEO_NORMAL)
    mil_ochenta = next(q for q in info.qualities if q.height == 1080)

    assert mil_ochenta.filesize_approx == 60_000_000
