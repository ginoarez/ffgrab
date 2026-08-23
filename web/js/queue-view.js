(function () {
  const contenedor = document.getElementById("queue");
  const vacio = document.getElementById("queue-empty");
  const tarjetas = new Map();

  const ETIQUETAS = {
    pending: "En espera",
    running: "Descargando",
    done: "Listo",
    failed: "Falló",
    cancelled: "Cancelado",
  };

  function crearTarjeta(job) {
    const nodo = document.createElement("div");
    nodo.className = "neu-sm job";
    nodo.innerHTML = `
      <div class="job-title"></div>
      <div class="progress"><div class="progress-fill"></div></div>
      <div class="job-foot">
        <span class="job-state"></span>
        <button class="job-cancel">Cancelar</button>
      </div>`;
    nodo.querySelector(".job-cancel").addEventListener("click", async () => {
      // Sin mirar la respuesta, un fallo del backend dejaria al usuario
      // pulsando un boton que no hace nada, sin rastro en ningun sitio.
      const r = await window.FFGrab.call("cancel", job.id);
      if (r && r.ok === false) {
        const estado = nodo.querySelector(".job-state");
        estado.textContent = "No se pudo cancelar: " + r.error;
        estado.title = r.error;
      }
    });
    contenedor.appendChild(nodo);
    tarjetas.set(job.id, nodo);
    return nodo;
  }

  function pintar(job) {
    const nodo = tarjetas.get(job.id) || crearTarjeta(job);

    nodo.className = "neu-sm job " + job.state;
    nodo.querySelector(".job-title").textContent = job.title;
    nodo.querySelector(".job-title").title = job.title;
    nodo.querySelector(".progress-fill").style.width = job.progress + "%";

    const estado = nodo.querySelector(".job-state");
    if (job.state === "failed") {
      estado.textContent = job.error || ETIQUETAS.failed;
      estado.title = job.error || "";
    } else if (job.state === "running") {
      estado.textContent = ETIQUETAS.running + (job.speed ? " · " + job.speed : "");
    } else {
      estado.textContent = ETIQUETAS[job.state] || job.state;
    }

    const terminado = ["done", "failed", "cancelled"].includes(job.state);
    nodo.querySelector(".job-cancel").classList.toggle("hidden", terminado);

    vacio.classList.add("hidden");
  }

  window.onJobChange = pintar;

  /* Al arrancar, recuperar lo que ya hubiera en la cola. */
  window.FFGrab.alEstarListo(async function () {
    const lista = await window.FFGrab.call("jobs");
    if (Array.isArray(lista)) lista.forEach(pintar);
  });
})();
