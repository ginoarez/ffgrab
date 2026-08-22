import pytest

from core.queue import DownloadQueue, JobCancelled, JobState


def runner_exitoso(job, on_progress):
    on_progress(50.0, "1.2MiB/s")
    return "/salida/" + job.title + ".mp4"


def runner_que_falla(job, on_progress):
    raise RuntimeError("el video es privado")


def test_encolar_deja_el_trabajo_pendiente():
    cola = DownloadQueue(runner=runner_exitoso)

    job = cola.enqueue("https://ejemplo.com/a", "Primero", {"mode": "video"})

    assert job.state is JobState.PENDING
    assert job.id == 1
    assert cola.jobs() == [job]


def test_los_ids_no_se_repiten():
    cola = DownloadQueue(runner=runner_exitoso)

    primero = cola.enqueue("https://ejemplo.com/a", "A", {})
    segundo = cola.enqueue("https://ejemplo.com/b", "B", {})

    assert primero.id != segundo.id


def test_run_next_completa_el_trabajo():
    cola = DownloadQueue(runner=runner_exitoso)
    cola.enqueue("https://ejemplo.com/a", "Primero", {})

    job = cola.run_next()

    assert job.state is JobState.DONE
    assert job.progress == 100.0
    assert job.output_path == "/salida/Primero.mp4"


def test_run_next_respeta_el_orden_de_llegada():
    cola = DownloadQueue(runner=runner_exitoso)
    cola.enqueue("https://ejemplo.com/a", "Primero", {})
    cola.enqueue("https://ejemplo.com/b", "Segundo", {})

    assert cola.run_next().title == "Primero"
    assert cola.run_next().title == "Segundo"


def test_run_next_devuelve_none_si_no_hay_pendientes():
    cola = DownloadQueue(runner=runner_exitoso)

    assert cola.run_next() is None


def test_un_fallo_no_detiene_la_cola():
    cola = DownloadQueue(runner=runner_que_falla)
    cola.enqueue("https://ejemplo.com/a", "Roto", {})
    cola.enqueue("https://ejemplo.com/b", "Tambien roto", {})

    primero = cola.run_next()
    segundo = cola.run_next()

    assert primero.state is JobState.FAILED
    assert primero.error == "el video es privado"
    assert segundo.state is JobState.FAILED


def test_cancelar_un_pendiente_lo_marca_sin_ejecutarlo():
    ejecutados = []

    def runner(job, on_progress):
        ejecutados.append(job.id)
        return "/salida/x.mp4"

    cola = DownloadQueue(runner=runner)
    job = cola.enqueue("https://ejemplo.com/a", "A", {})

    cola.cancel(job.id)

    assert job.state is JobState.CANCELLED
    assert cola.run_next() is None
    assert ejecutados == []


def test_cancelar_el_que_corre_lo_aborta_desde_el_progreso():
    referencia = {}

    def runner(job, on_progress):
        referencia["cola"].cancel(job.id)
        on_progress(10.0, "")  # debe lanzar JobCancelled
        raise AssertionError("no debería llegar aquí")

    cola = DownloadQueue(runner=runner)
    referencia["cola"] = cola
    cola.enqueue("https://ejemplo.com/a", "A", {})

    job = cola.run_next()

    assert job.state is JobState.CANCELLED


def test_el_progreso_lanza_jobcancelled_al_cancelado():
    referencia = {}
    capturada = {}

    def runner(job, on_progress):
        referencia["cola"].cancel(job.id)
        try:
            on_progress(10.0, "")
        except JobCancelled:
            capturada["si"] = True
            raise
        return "/salida/x.mp4"

    cola = DownloadQueue(runner=runner)
    referencia["cola"] = cola
    cola.enqueue("https://ejemplo.com/a", "A", {})
    cola.run_next()

    assert capturada.get("si") is True


def test_el_progreso_se_refleja_en_el_trabajo():
    cola = DownloadQueue(runner=runner_exitoso)
    cola.enqueue("https://ejemplo.com/a", "A", {})

    cola.run_next()

    # runner_exitoso reporta 50 y luego la cola lo cierra en 100 al terminar
    assert cola.jobs()[0].progress == 100.0


def test_on_change_se_dispara_en_cada_transicion():
    estados = []
    cola = DownloadQueue(runner=runner_exitoso, on_change=lambda j: estados.append(j.state))
    cola.enqueue("https://ejemplo.com/a", "A", {})

    cola.run_next()

    assert JobState.PENDING in estados
    assert JobState.RUNNING in estados
    assert JobState.DONE in estados


def test_cancelar_un_id_inexistente_no_explota():
    cola = DownloadQueue(runner=runner_exitoso)

    cola.cancel(999)  # no debe lanzar


def test_el_progreso_intermedio_se_reporta():
    """Verifica que los valores intermedios de progreso se reflejen en el job.

    Si se removiera la línea 'job.progress = porcentaje' de reportar(),
    este test fallaría porque solo vería 0.0 y 100.0, no 50.0.
    """
    progresos = []

    def runner(job, on_progress):
        on_progress(50.0, "1.2MiB/s")
        return "/salida/intermedio.mp4"

    cola = DownloadQueue(
        runner=runner,
        on_change=lambda j: progresos.append(j.progress)
    )
    cola.enqueue("https://ejemplo.com/a", "A", {})
    cola.run_next()

    # Debe haber capturado el progreso intermedio de 50.0, no solo 0.0 y 100.0
    assert 50.0 in progresos, f"Progreso intermedio 50.0 no encontrado en {progresos}"
