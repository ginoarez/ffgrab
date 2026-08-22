"""Diccionarios con la forma que devuelve yt-dlp, reducidos a lo que importa.

Se escriben a mano en vez de capturarse de la red para que los tests sean
deterministas y no dependan de que un video siga existiendo.
"""

VIDEO_NORMAL = {
    "id": "abc123",
    "title": "Un video de prueba",
    "duration": 213,
    "thumbnail": "https://ejemplo.com/thumb.jpg",
    "uploader": "Canal de prueba",
    "formats": [
        {"format_id": "140", "ext": "m4a", "vcodec": "none", "acodec": "mp4a.40.2", "abr": 129, "filesize": 3_400_000},
        {"format_id": "251", "ext": "webm", "vcodec": "none", "acodec": "opus", "abr": 141, "filesize": 3_600_000},
        {"format_id": "137", "ext": "mp4", "vcodec": "avc1.640028", "acodec": "none", "height": 1080, "fps": 30, "tbr": 4400, "filesize": 60_000_000},
        {"format_id": "248", "ext": "webm", "vcodec": "vp9", "acodec": "none", "height": 1080, "fps": 30, "tbr": 3800, "filesize": 52_000_000},
        {"format_id": "136", "ext": "mp4", "vcodec": "avc1.4d401f", "acodec": "none", "height": 720, "fps": 30, "tbr": 2200, "filesize": 30_000_000},
        {"format_id": "18", "ext": "mp4", "vcodec": "avc1.42001E", "acodec": "mp4a.40.2", "height": 360, "fps": 30, "tbr": 700, "filesize": 10_000_000},
    ],
    "subtitles": {},
    "automatic_captions": {},
}

VIDEO_4K_60FPS = {
    "id": "def456",
    "title": "Paisajes en 4K",
    "duration": 600,
    "thumbnail": "https://ejemplo.com/4k.jpg",
    "uploader": "Naturaleza",
    "formats": [
        {"format_id": "140", "ext": "m4a", "vcodec": "none", "acodec": "mp4a.40.2", "abr": 129},
        {"format_id": "315", "ext": "webm", "vcodec": "vp9", "acodec": "none", "height": 2160, "fps": 60, "tbr": 20000},
        {"format_id": "401", "ext": "mp4", "vcodec": "av01.0.12M.08", "acodec": "none", "height": 2160, "fps": 60, "tbr": 15000},
        {"format_id": "299", "ext": "mp4", "vcodec": "avc1.64002a", "acodec": "none", "height": 1080, "fps": 60, "tbr": 5500},
    ],
    "subtitles": {},
    "automatic_captions": {},
}

SOLO_AUDIO = {
    "id": "ghi789",
    "title": "Un podcast",
    "duration": 3600,
    "thumbnail": "https://ejemplo.com/pod.jpg",
    "uploader": "Programa",
    "formats": [
        {"format_id": "140", "ext": "m4a", "vcodec": "none", "acodec": "mp4a.40.2", "abr": 129},
    ],
    "subtitles": {},
    "automatic_captions": {},
}

FORMATOS_ROTOS = {
    "id": "jkl012",
    "title": "Video con metadatos incompletos",
    "duration": 0,
    "thumbnail": "",
    "uploader": "",
    "formats": [
        {"format_id": "sin-altura", "ext": "mp4", "vcodec": "avc1", "acodec": "none"},
        {"format_id": "sin-codec", "ext": "mp4", "height": 720},
        {"format_id": "140", "ext": "m4a", "vcodec": "none", "acodec": "mp4a.40.2", "abr": 129},
        {"format_id": "137", "ext": "mp4", "vcodec": "avc1.640028", "acodec": "none", "height": 1080, "fps": 30, "tbr": 4400},
    ],
    "subtitles": {},
    "automatic_captions": {},
}

VIDEO_SIN_AUDIO_EMPAREJABLE = {
    "id": "mno345",
    "title": "Solo pistas de video",
    "duration": 100,
    "thumbnail": "",
    "uploader": "",
    "formats": [
        {"format_id": "137", "ext": "mp4", "vcodec": "avc1.640028", "acodec": "none", "height": 1080, "fps": 30, "tbr": 4400},
    ],
    "subtitles": {},
    "automatic_captions": {},
}
