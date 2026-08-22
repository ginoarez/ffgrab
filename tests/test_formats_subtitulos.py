from core.formats import normalize
from tests.fixtures.info_dicts import (
    VIDEO_CON_SUBTITULOS,
    VIDEO_MANUAL_ALFABETICAMENTE_POSTERIOR,
    VIDEO_NORMAL,
)


def test_sin_subtitulos_devuelve_tupla_vacia():
    assert normalize(VIDEO_NORMAL).subtitles == ()


def test_los_manuales_van_primero_y_ordenados():
    pistas = normalize(VIDEO_CON_SUBTITULOS).subtitles
    manuales = [p for p in pistas if not p.is_auto]

    assert [p.lang_code for p in manuales] == ["en", "es"]


def test_marca_los_autogenerados():
    pistas = normalize(VIDEO_CON_SUBTITULOS).subtitles
    portugues = next(p for p in pistas if p.lang_code == "pt")

    assert portugues.is_auto is True


def test_el_manual_gana_cuando_el_idioma_esta_en_ambos():
    pistas = normalize(VIDEO_CON_SUBTITULOS).subtitles
    espanol = [p for p in pistas if p.lang_code == "es"]

    assert len(espanol) == 1
    assert espanol[0].is_auto is False


def test_usa_el_nombre_legible_cuando_existe():
    pistas = normalize(VIDEO_CON_SUBTITULOS).subtitles
    ingles = next(p for p in pistas if p.lang_code == "en")

    assert ingles.lang_name == "English"


def test_cae_al_codigo_de_idioma_si_no_hay_nombre():
    pistas = normalize(VIDEO_CON_SUBTITULOS).subtitles
    frances = next(p for p in pistas if p.lang_code == "fr")

    assert frances.lang_name == "fr"


def test_los_autogenerados_van_despues_de_todos_los_manuales():
    pistas = normalize(VIDEO_CON_SUBTITULOS).subtitles

    primer_auto = next(i for i, p in enumerate(pistas) if p.is_auto)
    assert all(not p.is_auto for p in pistas[:primer_auto])
    assert all(p.is_auto for p in pistas[primer_auto:])


def test_los_autogenerados_van_ordenados():
    pistas = normalize(VIDEO_CON_SUBTITULOS).subtitles
    automaticos = [p.lang_code for p in pistas if p.is_auto]

    assert automaticos == ["fr", "pt"]


def test_manual_gana_sobre_automatico_incluso_si_alfabeticamente_posterior():
    pistas = normalize(VIDEO_MANUAL_ALFABETICAMENTE_POSTERIOR).subtitles
    codigos = [p.lang_code for p in pistas]

    assert codigos == ["zz", "aa"]
    assert pistas[0].is_auto is False
    assert pistas[1].is_auto is True


def test_secuencia_completa_de_idiomas_en_orden():
    pistas = normalize(VIDEO_CON_SUBTITULOS).subtitles
    codigos = [p.lang_code for p in pistas]

    assert codigos == ["en", "es", "fr", "pt"]
