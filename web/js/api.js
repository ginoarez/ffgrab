/* Envoltura del puente de pywebview. Todas las llamadas son promesas. */
window.FFGrab = {
  state: { info: null, mode: "video", container: "mp4", audioFormat: "mp3" },

  async call(metodo, ...args) {
    const api = window.pywebview && window.pywebview.api;
    if (!api || typeof api[metodo] !== "function") {
      return { ok: false, error: "El puente con Python no está disponible." };
    }
    try {
      return await api[metodo](...args);
    } catch (error) {
      return { ok: false, error: String(error) };
    }
  },
};

window.FFGrab.alEstarListo = function (fn) {
  function listo() {
    return !!(window.pywebview && window.pywebview.api
              && typeof window.pywebview.api.deps_status === "function");
  }
  if (listo()) { fn(); return; }
  var intentos = 0;
  var t = setInterval(function () {
    if (listo()) { clearInterval(t); fn(); }
    else if (++intentos > 100) { clearInterval(t); }   // ~5s y se rinde
  }, 50);
};
