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
