# FFGrab — Diseño

**Fecha:** 2026-08-22
**Estado:** aprobado, listo para plan de implementación

## Qué es

Aplicación de escritorio para descargar videos eligiendo calidad, formato, subtítulos e
idioma, con cola de descargas y modo solo-audio. Se publicará como open source en GitHub.

El trabajo pesado lo hacen dos herramientas existentes: **yt-dlp** habla con los sitios,
enumera lo disponible y descarga; **ffmpeg** une las pistas y convierte. FFGrab es la
interfaz que las coordina.

## Decisiones tomadas

| Decisión | Elegido | Por qué |
|---|---|---|
| Formato de app | Python + pywebview (ventana nativa) | La interfaz es HTML/CSS/JS real, así que el estilo se construye sin restricciones, pero se ve como app de escritorio. ~15 MB frente a los ~150 MB de Electron, y yt-dlp se usa como librería en vez de como binario externo. |
| Motor | yt-dlp + ffmpeg | ffmpeg solo no sabe hablar con los sitios ni enumerar pistas. yt-dlp hace eso y ya invoca a ffmpeg internamente. |
| Layout | Dos paneles | Controles a la izquierda, cola siempre visible a la derecha. Con cola en v1, la columna única obliga a hacer scroll y el wizard obliga a recorrerlo entero por cada video. |
| Estilo visual | Neumorfismo oscuro + acento azul | Elegido sobre claymorphism. El acento en la acción principal y en el progreso resuelve el problema de contraste típico del neumorfismo. |
| Concurrencia | Una descarga a la vez | Varias en paralelo sobre la misma conexión no terminan antes, arrastran todas las barras a la vez y aumentan el riesgo de que el sitio limite el tráfico. |
| ffmpeg ausente | Detectar + botón de descarga | Cero fricción para quien clone el repo, y usa el build completo en vez de uno reducido. |
| Versión de yt-dlp | Aviso + botón para actualizar | yt-dlp saca versiones cada pocos días porque los sitios cambian. Sin aviso, el síntoma es "de repente dejó de funcionar" sin ninguna pista. |

## Alcance

**Dentro de v1:** un video por vez en el panel de entrada · selector de calidad · selector
de contenedor · subtítulos con selector de idioma · extracción solo-audio (mp3/m4a) ·
cola secuencial con progreso por item · descarga y verificación de ffmpeg · aviso de
versión de yt-dlp.

**Fuera de v1:** playlists y canales completos · subtítulos incrustados sobre la imagen
(burn-in) · descargas paralelas · empaquetado a `.exe` · programación de descargas.

Playlists y burn-in se documentan en el README como trabajo futuro.

## Arquitectura

```
ffgrab/
├── app.py                  ventana, puente JS↔Python, arranque
├── core/
│   ├── deps.py             detecta/instala ffmpeg, revisa versión de yt-dlp
│   ├── probe.py            lee el link, devuelve qué hay disponible
│   ├── formats.py          traduce formatos crudos a opciones legibles
│   ├── download.py         ejecuta UNA descarga, reporta progreso
│   └── queue.py            cola secuencial: estados, orden, cancelación
├── web/
│   ├── index.html
│   ├── css/                tokens.css · neu.css · layout.css
│   └── js/                 api.js · ui.js · queue-view.js
├── docs/superpowers/specs/
├── tests/
│   └── fixtures/           respuestas JSON reales de yt-dlp
├── requirements.txt
├── README.md
└── LICENSE
```

**El corte principal está entre `core/` y `web/`: `core/` no sabe que existe una
interfaz.** Recibe datos y devuelve datos. Eso permite probarlo entero sin abrir ninguna
ventana, y deja la puerta abierta a una CLI sin reescribir nada.

### Módulos

**`core/formats.py`** — Sin estado, sin red, funciones puras.

```python
@dataclass
class QualityOption:
    height: int              # 1080
    label: str               # "1080p60"
    fps: int
    ext: str                 # "mp4"
    video_format_id: str
    audio_format_id: str | None
    needs_merge: bool
    filesize_approx: int | None

@dataclass
class SubtitleTrack:
    lang_code: str           # "es"
    lang_name: str           # "Español"
    is_auto: bool            # autogenerado por reconocimiento de voz

@dataclass
class VideoInfo:
    id: str
    title: str
    duration: int
    thumbnail_url: str
    uploader: str
    qualities: list[QualityOption]
    subtitles: list[SubtitleTrack]

def normalize(raw_info: dict) -> VideoInfo: ...
```

Existe como módulo aparte porque yt-dlp devuelve entre 20 y 50 formatos por video, en su
mayoría duplicados o pistas sueltas de solo-video o solo-audio. Colapsarlos a seis
opciones que un humano entienda es lógica con reglas propias, y es donde más van a
aparecer los bugs. Aislada y pura, se prueba con fixtures y sin red.

Reglas de colapso: agrupar por altura; dentro de cada altura preferir el códec más
compatible antes que el más pequeño; descartar alturas sin pista de audio emparejable;
marcar `needs_merge` cuando video y audio vengan separados. Los subtítulos autogenerados
se incluyen con `is_auto=True` y la interfaz los muestra etiquetados.

**`core/probe.py`** — `probe(url) -> VideoInfo`. Llama a yt-dlp sin descargar y delega en
`formats.normalize`. Única responsabilidad: consultar y traducir errores de red o de sitio
a excepciones propias.

**`core/download.py`** — `run(job, on_progress) -> Path`. Ejecuta una descarga con las
opciones elegidas. El progreso sale por callback. Aquí viven el armado de opciones de
yt-dlp, la incrustación de subtítulos y la conversión a audio.

**`core/queue.py`** — Máquina de estados y un hilo trabajador.
Estados: `PENDING → RUNNING → DONE | FAILED | CANCELLED`.
Un `Job` guarda id, url, la `VideoInfo`, las opciones elegidas, estado, progreso y error.

**`core/deps.py`**

```python
def ffmpeg_status() -> FFmpegStatus      # FOUND | MISSING | BROKEN, con ruta y versión
def install_ffmpeg(on_progress) -> Path  # descarga, descomprime y verifica
def ytdlp_update_available() -> str | None
```

Busca ffmpeg primero en la carpeta local del proyecto, después en el PATH del sistema.
Tras descargar, verifica ejecutando `ffmpeg -version`: un archivo presente pero corrupto
debe reportarse como `BROKEN`, no como `FOUND`.

**`app.py`** — Crea la ventana y expone una clase `Api` al JS: `probe`, `enqueue`,
`cancel`, `queue_state`, `deps_status`, `install_ffmpeg`, `update_ytdlp`, `choose_folder`.
Las llamadas del puente son bloqueantes, así que todo lo que tarde corre en un hilo y
avisa a la interfaz empujando eventos con `evaluate_js`.

## Flujo de datos

1. Al arrancar, `deps.ffmpeg_status()`. Si no está `FOUND`, se muestra la compuerta de
   dependencias y nada más.
2. Se pega un link → `probe.probe(url)` → la interfaz pinta miniatura, título, duración,
   calidades, contenedores e idiomas de subtítulo.
3. Se eligen opciones y se pulsa "Añadir a la cola" → `queue.enqueue(job)`.
4. El hilo trabajador toma el primer `PENDING` y llama a `download.run`.
5. El callback de progreso empuja porcentaje y velocidad a la tarjeta correspondiente.
6. yt-dlp descarga, ffmpeg une, se incrustan subtítulos y se escribe el `.srt` si
   corresponde. El job pasa a `DONE`.

## Casos especiales

**Solo audio** omite la selección de calidad de video: baja la mejor pista de audio y
ffmpeg convierte a mp3 o m4a.

**Subtítulos** hacen dos cosas a la vez, cada una con su interruptor: se incrustan como
pista dentro del contenedor y se guarda el `.srt` al lado. Ambos activos por defecto.

**MP4 con subtítulos incrustados**: MP4 los soporta de forma limitada y algunos
reproductores los ignoran. Si se combinan, la interfaz avisa en el momento y ofrece MKV.
No cambia el contenedor por su cuenta — avisa y el usuario decide.

## Manejo de errores

**A nivel de app**, solo las dependencias. Si falta ffmpeg, la aplicación no se muestra:
se muestra el botón que lo instala. Una interfaz que funciona hasta el final y revienta al
unir el archivo es el peor resultado posible.

**A nivel de tarjeta**, todo lo demás. Un video privado, geobloqueado o eliminado marca
*ese* job como `FAILED` con el motivo en texto claro y un botón de reintentar; la cola
continúa con el siguiente. Los cortes de red los reintenta yt-dlp; agotados los intentos,
el job queda fallido y reintentable. Disco lleno y permisos de escritura se comprueban
antes de empezar la descarga, no a mitad.

Un link de un sitio no soportado dice exactamente eso, nunca "error desconocido".

## Diseño visual

Neumorfismo oscuro. Todo elemento comparte el color exacto del fondo y se distingue solo
por dos sombras enfrentadas: oscura abajo-derecha, clara arriba-izquierda. Los elementos
de entrada usan las mismas sombras en `inset`, que los hace ver hundidos.

```css
:root {
  --bg:           #2f333b;
  --shadow-dark:  #22252b;
  --shadow-light: #3d434e;
  --ink:          #c2c9d5;
  --accent:       #5b8fd6;
  --accent-ink:   #ffffff;

  --radius:   13px;
  --radius-sm: 9px;

  --neu-out: 6px 6px 12px var(--shadow-dark), -6px -6px 12px var(--shadow-light);
  --neu-in:  inset 4px 4px 8px var(--shadow-dark), inset -4px -4px 8px var(--shadow-light);
}
```

El radio se mantiene entre 9 y 16px: por encima de eso el relieve se deshace en las
esquinas y el efecto se pierde.

El acento sólido se reserva para **la acción principal y las barras de progreso**, y para
nada más. Es lo que hace que la acción central se distinga de una tarjeta cualquiera y que
el avance de cada descarga se lea de un vistazo desde lejos.

Toda la definición del efecto vive en `tokens.css` y `neu.css`. Cambiar la paleta debe ser
cambiar variables, nunca editar sombras repartidas por el código.

## Pruebas

TDD sobre `core/`, que es donde está la lógica.

- **`formats.py`** — el grueso del esfuerzo. Fixtures con respuestas reales de yt-dlp:
  video normal, solo-audio, 4K con 60fps, sin subtítulos, con quince idiomas, y uno con
  formatos rotos o incompletos. Se verifica qué opciones salen. Sin red.
- **`queue.py`** — la máquina de estados: encolar, completar, fallar, cancelar en espera y
  cancelar el que está corriendo.
- **`deps.py`** — ffmpeg presente, ausente, y presente pero corrupto.

`probe.py` y `download.py` tocan la red, así que se prueban con el cliente de yt-dlp
simulado. Una prueba de humo real contra un video corto queda marcada aparte, para correr
a mano y no en cada commit.

## Dependencias

`requirements.txt`: `yt-dlp`, `pywebview`. Nada más — sin framework web, sin bundler, sin
dependencias de frontend. La interfaz es HTML, CSS y JavaScript sin compilar.

ffmpeg no se distribuye con el repo; se detecta o se descarga en la primera ejecución a
una carpeta local ignorada por git.

## README

Debe cubrir: qué hace y una captura · instalación · cómo se resuelve ffmpeg · las
funciones con capturas · trabajo futuro (playlists, burn-in, empaquetado a `.exe`) ·
licencia.

Dos secciones que no son opcionales en un repo de este tipo:

**Créditos.** El trabajo real lo hacen yt-dlp y ffmpeg. Ambos deben estar acreditados con
enlace en un lugar visible, y debe quedar explícito que FFGrab no está afiliado a ninguno
de los dos proyectos — especialmente relevante porque el nombre empieza con `ff`.

**Uso responsable.** Una nota breve indicando que la herramienta es para contenido que el
usuario tiene derecho a descargar, y que respetar los términos de servicio de cada sitio y
los derechos de autor queda de su lado.

**Licencia: MIT.** ffmpeg se distribuye bajo LGPL o GPL según el build, y yt-dlp es
Unlicense. Como FFGrab no redistribuye ninguno de los dos binarios —los invoca o los
descarga en tiempo de ejecución— no hay contagio de licencia y la elección queda libre.
MIT es la más permisiva y la que menos fricción impone a quien quiera reutilizar el
código. Cambiarla es trivial mientras el repo siga siendo privado.

## Futuro

Playlists y canales · subtítulos incrustados sobre la imagen · empaquetado a `.exe` con
PyInstaller · descargas paralelas configurables · recordar preferencias entre sesiones.
