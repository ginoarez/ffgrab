# FFGrab

Descargador de video de escritorio: eliges calidad, formato, subtítulos e idioma, y los encolas.

![La ventana de FFGrab](docs/captura.png)

## Qué hace

- **Calidad** — una opción por resolución, quedándose con el códec más compatible de cada una. Un archivo que se reproduce en cualquier reproductor vale más que uno pequeño que no.
- **Formato** — MP4 o MKV. Si eliges MP4 con subtítulos incrustados te avisa de que algunos reproductores los ignoran, y te ofrece MKV. No te cambia el contenedor por su cuenta.
- **Subtítulos** — por idioma, incrustados como pista y/o guardados en un `.srt` aparte, cada cosa con su interruptor. Los autogenerados por reconocimiento de voz aparecen siempre etiquetados como tales, nunca mezclados en silencio con los escritos por personas.
- **Solo audio** — mp3 o m4a.
- **Cola** — una descarga a la vez, con progreso y cancelación por item. Varias en paralelo sobre la misma conexión no terminan antes: solo arrastran todas las barras a la vez.

## Instalación

Necesitas Python 3.11 o superior.

```bash
git clone https://github.com/ginoarez/ffgrab
cd ffgrab
python run.py
```

En Windows también funciona con doble clic en **`run.py`**. La primera vez crea
un entorno local en `.venv`, instala las dependencias y abre la app; las
siguientes va directo.

> **Por qué `run.py` y no `python app.py`.** En Windows suelen convivir varios
> Python: el de la Microsoft Store, el de python.org, entornos virtuales. Si
> `python` resuelve a uno que no tiene las dependencias, la ventana abre igual
> pero consultar un enlace se queda colgado para siempre, sin decir por qué. El
> lanzador fija el intérprete y evita ese fallo, que es difícil de diagnosticar
> precisamente porque la app *parece* arrancar bien. Si el Python que lo abre
> es demasiado viejo, busca uno mejor en el sistema en vez de rendirse.

### Un ejecutable, si lo prefieres

```bash
pip install pyinstaller
pyinstaller ffgrab.spec
```

Deja `dist/FFGrab.exe`, sin consola y sin dependencias que instalar. No hay
`.exe` publicado acá a propósito: un binario suelto descargado de internet es
justo lo que no conviene ejecutar a ciegas, y con el código a la vista puedes
construir el tuyo. ffmpeg se descarga junto al ejecutable la primera vez.

## Sobre ffmpeg

No hace falta instalarlo a mano. FFGrab lo busca en su propia carpeta y después en el PATH del sistema; si no lo encuentra, la aplicación **no se muestra** — en su lugar aparece un botón que lo descarga. Es deliberado: una interfaz que funciona hasta el final y revienta justo al unir el video es el peor resultado posible.

Si encuentra un ffmpeg que existe pero no responde, lo reporta como dañado en vez de darlo por bueno.

## Sesión: cuando el sitio pide iniciar sesión

Muchos sitios responden a una consulta anónima con una verificación anti-bot (*"Sign in to confirm you're not a bot"*). El desplegable **Sesión** le dice a FFGrab de qué navegador leer tus cookies para saltarla. Cambiarlo reconsulta el enlace automáticamente.

Tres cosas que conviene saber, porque son fáciles de encontrarse:

- **Firefox** suele funcionar sin problemas, pero solo sirve si tienes la sesión iniciada **en ese** navegador.
- **Chrome y Edge** bloquean su base de datos de cookies mientras están abiertos, y las versiones recientes la cifran de forma que impide leerla. Ciérralos del todo antes de intentarlo.
- Si nada de lo anterior funciona, exporta un `cookies.txt` con una extensión de navegador y elige **"Archivo cookies.txt…"** en el desplegable Sesión para señalarlo.

## Certificados: si todo falla con `CERTIFICATE_VERIFY_FAILED`

Python solo confía en su propio paquete de certificados públicos. Cuando un antivirus o un proxy corporativo inspecciona el tráfico HTTPS, instala su certificado raíz en el almacén de Windows — que el navegador sí usa y Python no. El resultado es que el navegador funciona pero yt-dlp no alcanza ningún sitio.

FFGrab lo resuelve validando contra el almacén del sistema. Si aun así te aparece, comprueba que `truststore` se instaló con las dependencias.

## Créditos

El trabajo pesado no lo hace FFGrab. Lo hacen dos proyectos ajenos y excelentes:

- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** habla con los sitios, enumera lo disponible y descarga.
- **[FFmpeg](https://ffmpeg.org/)** une las pistas de video y audio, incrusta subtítulos y convierte formatos.

> FFGrab es un proyecto independiente y **no está afiliado ni respaldado** por los proyectos yt-dlp o FFmpeg. El nombre empieza por `ff` como guiño, no como señal de pertenencia.

## Uso responsable

Esta herramienta es para contenido que tienes derecho a descargar. Respetar los términos de servicio de cada sitio y los derechos de autor del material queda de tu lado.

## Trabajo futuro

Playlists y canales completos · subtítulos incrustados sobre la imagen (burn-in) · descargas paralelas configurables · recordar preferencias entre sesiones.

**Deliberadamente fuera de esta versión:** un botón para actualizar yt-dlp desde la propia app. El aviso te dice que hay una versión nueva, pero actualizarla es correr `pip install -U yt-dlp` a mano. Correr `pip install` contra el propio intérprete en caliente, en medio de una sesión que puede tener una descarga corriendo, es frágil, y un paquete a medio actualizar bajo un proceso que sigue vivo es un mal modo de fallar. Mejor decir la verdad en el aviso que fingir que hay un botón.

## Licencia

MIT — ver [LICENSE](LICENSE).
