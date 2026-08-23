(function () {
  const $ = (id) => document.getElementById(id);
  const S = window.FFGrab.state;

  /* --- grupos de chips mutuamente excluyentes --- */
  function grupo(botones, alElegir) {
    botones.forEach(([boton, valor]) => {
      boton.addEventListener("click", () => {
        botones.forEach(([otro]) => otro.setAttribute("aria-pressed", "false"));
        boton.setAttribute("aria-pressed", "true");
        alElegir(valor);
      });
    });
  }

  grupo([[$("mode-video"), "video"], [$("mode-audio"), "audio"]], (valor) => {
    S.mode = valor;
    $("video-controls").classList.toggle("hidden", valor !== "video");
    $("audio-controls").classList.toggle("hidden", valor === "video");
    $("subs-field").classList.toggle("hidden", valor === "audio");
  });

  grupo([[$("cont-mp4"), "mp4"], [$("cont-mkv"), "mkv"]], (valor) => {
    S.container = valor;
    revisarAvisoMp4();
  });

  grupo([[$("aud-mp3"), "mp3"], [$("aud-m4a"), "m4a"]], (valor) => {
    S.audioFormat = valor;
  });

  /* --- aviso de MP4 con subtítulos incrustados --- */
  function revisarAvisoMp4() {
    const hayIdioma = $("subtitle").value !== "";
    const mostrar = S.container === "mp4" && hayIdioma && $("embed-subs").checked;
    $("mp4-warning").classList.toggle("hidden", !mostrar);
  }

  $("subtitle").addEventListener("change", revisarAvisoMp4);
  $("embed-subs").addEventListener("change", revisarAvisoMp4);

  /* --- consulta del enlace --- */
  let ultimaConsulta = 0;

  async function consultar(url) {
    const marca = ++ultimaConsulta;
    $("placeholder").textContent = "Consultando el enlace…";
    $("placeholder").classList.remove("hidden");
    $("details").classList.add("hidden");
    $("probe-error").classList.add("hidden");

    const respuesta = await window.FFGrab.call("probe", url);
    if (marca !== ultimaConsulta) return; // llegó tarde, ya hay otra consulta

    if (!respuesta.ok) {
      $("placeholder").classList.add("hidden");
      $("probe-error").textContent = respuesta.error;
      $("probe-error").classList.remove("hidden");
      return;
    }

    S.info = respuesta;
    pintarDetalles(respuesta);
  }

  function pintarDetalles(info) {
    $("placeholder").classList.add("hidden");
    $("details").classList.remove("hidden");

    $("thumb").src = info.thumbnail_url || "";
    $("meta-title").textContent = info.title;
    $("meta-sub").textContent = [info.uploader, formatearDuracion(info.duration)]
      .filter(Boolean)
      .join(" · ");

    const quality = $("quality");
    quality.replaceChildren();
    info.qualities.forEach((q, i) => {
      const opcion = new Option(`${q.label} · ${q.ext}${tamano(q)}`, String(i));
      quality.appendChild(opcion);
    });

    const subtitle = $("subtitle");
    subtitle.replaceChildren();
    subtitle.appendChild(new Option("Sin subtítulos", ""));
    info.subtitles.forEach((s) => {
      const opcion = new Option(
        `${s.lang_name}${s.is_auto ? " (autogenerado)" : ""}`,
        s.lang_code
      );
      opcion.dataset.auto = String(s.is_auto);
      subtitle.appendChild(opcion);
    });

    $("mode-audio").disabled = false;
    if (info.qualities.length === 0) {
      $("mode-audio").click();
      $("mode-video").disabled = true;
    } else {
      $("mode-video").disabled = false;
    }
    revisarAvisoMp4();
  }

  function tamano(q) {
    if (!q.filesize_approx) return "";
    return " · " + (q.filesize_approx / 1048576).toFixed(0) + " MB";
  }

  function formatearDuracion(segundos) {
    if (!segundos) return "";
    const m = Math.floor(segundos / 60);
    const s = String(segundos % 60).padStart(2, "0");
    return `${m}:${s}`;
  }

  /* --- opciones que se envían a Python --- */
  window.FFGrab.buildOptions = function () {
    const elegido = $("subtitle").selectedOptions[0];
    const idioma = $("subtitle").value || null;
    const esAuto = elegido ? elegido.dataset.auto === "true" : false;

    if (S.mode === "audio") {
      return {
        mode: "audio",
        audio_format: S.audioFormat,
        subtitle_lang: null,
        subtitle_auto: false,
        embed_subs: false,
        keep_srt: false,
      };
    }

    const calidad = S.info.qualities[Number($("quality").value)];
    return {
      mode: "video",
      video_format_id: calidad.video_format_id,
      audio_format_id: calidad.audio_format_id,
      container: S.container,
      subtitle_lang: idioma,
      subtitle_auto: esAuto,
      embed_subs: $("embed-subs").checked,
      keep_srt: $("keep-srt").checked,
      filesize_approx: calidad.filesize_approx,
    };
  };

  /* --- sesion (cookies) ---
     Muchos sitios rechazan la consulta anonima con una verificacion anti-bot.
     Leer las cookies del navegador donde ya hay sesion iniciada es el
     mecanismo que soporta yt-dlp para saltarla. */
  $("cookies").addEventListener("change", async function () {
    var origen = $("cookies").value;
    var r = await window.FFGrab.call("set_cookies", origen);
    var hint = $("cookies-hint");
    if (r && r.ok === false) {
      hint.textContent = "No se pudo usar esa sesión: " + r.error;
      hint.classList.remove("hidden");
      return;
    }
    hint.classList.add("hidden");
    var url = $("url").value.trim();
    if (url) consultar(url);   // reintenta con la sesion nueva
  });

  /* --- carpeta de destino --- */
  async function mostrarCarpeta(ruta) {
    if (typeof ruta !== "string" || !ruta) {
      console.warn("mostrarCarpeta: valor no usable", ruta);
      return;
    }
    const corta = ruta.length > 46 ? "…" + ruta.slice(-45) : ruta;
    $("outdir-label").textContent = "Guardando en " + corta;
    $("outdir-label").title = ruta;
  }

  $("outdir-label").addEventListener("click", async () => {
    const elegida = await window.FFGrab.call("choose_folder");
    mostrarCarpeta(elegida);
  });

  async function alArrancar() {
    mostrarCarpeta(await window.FFGrab.call("current_folder"));
  }

  window.FFGrab.alEstarListo(alArrancar);


  /* --- compuerta de dependencias ---
     Si falta ffmpeg la app no se muestra: se muestra el boton que lo instala.
     Una interfaz que funciona hasta el final y revienta al unir el archivo es
     el peor resultado posible. */
  window.onFfmpegProgress = function (porcentaje) {
    $("gate-fill").style.width = porcentaje + "%";
  };

  async function revisarDependencias() {
    var estado = await window.FFGrab.call("deps_status");
    if (!estado || estado.ok !== true) return;

    if (estado.ffmpeg !== "found") {
      if (estado.ffmpeg === "broken") {
        $("gate-title").textContent = "ffmpeg está dañado";
        $("gate-text").textContent =
          "Se encontró ffmpeg pero no responde, así que el archivo está " +
          "incompleto o corrupto. Descargar una copia nueva lo soluciona.";
      }
      $("gate").classList.remove("hidden");
      return;
    }
    $("gate").classList.add("hidden");

    if (estado.ytdlp_update) {
      $("ytdlp-text").textContent =
        "Hay una versión nueva de yt-dlp (" + estado.ytdlp_update + "). " +
        "Los sitios cambian seguido y una copia vieja deja de funcionar.";
      $("ytdlp-banner").classList.remove("hidden");
    }
  }

  $("gate-install").addEventListener("click", async function () {
    $("gate-install").disabled = true;
    $("gate-install").textContent = "Descargando…";
    $("gate-progress").classList.remove("hidden");
    var r = await window.FFGrab.call("install_ffmpeg");
    if (r && r.ok) {
      revisarDependencias();
      $("gate-install").disabled = false;
      $("gate-install").textContent = "Descargar ffmpeg";
      return;
    }
    $("gate-text").textContent = "No se pudo descargar: " + (r ? r.error : "error desconocido");
    $("gate-install").disabled = false;
    $("gate-install").textContent = "Reintentar";
  });

  window.FFGrab.alEstarListo(revisarDependencias);

  /* --- eventos --- */
  let temporizador = null;
  $("url").addEventListener("input", (evento) => {
    const url = evento.target.value.trim();
    clearTimeout(temporizador);
    if (!url) return;
    temporizador = setTimeout(() => consultar(url), 450);
  });

  $("add").addEventListener("click", async () => {
    if (!S.info) return;
    $("add").disabled = true;
    const respuesta = await window.FFGrab.call("enqueue", {
      url: $("url").value.trim(),
      title: S.info.title,
      options: window.FFGrab.buildOptions(),
    });
    $("add").disabled = false;
    if (!respuesta.ok) {
      $("probe-error").textContent = respuesta.error;
      $("probe-error").classList.remove("hidden");
    }
  });
})();
