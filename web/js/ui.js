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

    $("quality").innerHTML = info.qualities
      .map((q, i) => `<option value="${i}">${q.label} · ${q.ext}${tamano(q)}</option>`)
      .join("");

    const sinSubs = '<option value="">Sin subtítulos</option>';
    $("subtitle").innerHTML =
      sinSubs +
      info.subtitles
        .map(
          (s) =>
            `<option value="${s.lang_code}" data-auto="${s.is_auto}">` +
            `${s.lang_name}${s.is_auto ? " (autogenerado)" : ""}</option>`
        )
        .join("");

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

  /* --- carpeta de destino --- */
  async function mostrarCarpeta(ruta) {
    if (typeof ruta !== "string" || !ruta) return;
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

  if (window.pywebview && window.pywebview.api) {
    alArrancar();
  } else {
    window.addEventListener("pywebviewready", alArrancar);
  }

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
