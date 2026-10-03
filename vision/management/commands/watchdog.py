"""Revisa el estado del sistema y avisa por el Notifier. Corre por timer cada 5 min.

`revisar` es pura y recibe todo inyectado (reloj, uso de disco, datos ya leídos)
para poder probar cada condición por separado sin systemd, disco ni red.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand

# horas máximas sin correr antes de alertar (un job diario tolera ~26 h)
JOBS_DIARIOS = {"corpus": 26, "insights": 26, "backup": 26}
UMBRAL_DISCO = 0.90
RESTORE_CHECK_MAX_DIAS = 2


def revisar(ahora, camaras_caidas, jobs_ultima, uso_disco,
            clips_vencidos_en_disco, restore_check_dias):
    hallazgos = []
    for salud in camaras_caidas:
        hallazgos.append({"tipo": "camara_caida",
                          "business_id": salud.camera.business_id,
                          "mensaje": f"Cámara {salud.camera.name} sin señal."})
    for job, horas in JOBS_DIARIOS.items():
        ultima = jobs_ultima.get(job)
        if ultima is None or (ahora - ultima) > timedelta(hours=horas):
            hallazgos.append({"tipo": "job", "business_id": None,
                              "mensaje": f"El job '{job}' no ha corrido en {horas} h."})
    if uso_disco >= UMBRAL_DISCO:
        hallazgos.append({"tipo": "disco", "business_id": None,
                          "mensaje": f"Disco al {uso_disco:.0%}."})
    if clips_vencidos_en_disco:
        hallazgos.append({"tipo": "clips", "business_id": None,
                          "mensaje": f"{clips_vencidos_en_disco} clips vencidos siguen en disco."})
    if restore_check_dias is None or restore_check_dias > RESTORE_CHECK_MAX_DIAS:
        hallazgos.append({"tipo": "backup", "business_id": None,
                          "mensaje": "restore_check no pasa hace más de "
                                     f"{RESTORE_CHECK_MAX_DIAS} días."})
    return hallazgos


class Command(BaseCommand):
    help = "Revisa cámaras, jobs, disco y respaldos; alerta por el Notifier."

    def handle(self, *args, **opts):
        import shutil

        from django.conf import settings
        from django.utils import timezone

        from analytics.models import EventClip, JobRun
        from analytics.notifier import Notifier, WebhookBackend
        from cameras.models import CameraHealth

        ahora = timezone.now()
        caidas = list(CameraHealth.objects.select_related("camera")
                      .filter(ultimo_latido__lt=ahora - timedelta(seconds=300)))
        jobs_ultima = {j.nombre: j.terminado_en for j in JobRun.objects.all()}
        uso = 1.0 - shutil.disk_usage(settings.BASE_DIR).free / shutil.disk_usage(settings.BASE_DIR).total
        clips = EventClip.objects.filter(expires_at__lt=ahora).count()
        rc = JobRun.ultima("restore_check")
        rc_dias = None if rc is None else (ahora - rc.terminado_en).days

        hallazgos = revisar(ahora, caidas, jobs_ultima, uso, clips, rc_dias)
        self._despachar(hallazgos, Notifier(WebhookBackend()))
        self.stdout.write(f"{len(hallazgos)} hallazgos.")

    def _despachar(self, hallazgos, notifier):
        from analytics.models import AlertRule
        for h in hallazgos:
            reglas = AlertRule.objects.filter(tipo_evento="camara_caida", activa=True)
            if h["business_id"] is not None:
                reglas = reglas.filter(business_id=h["business_id"])
            for regla in reglas:
                notifier.notificar(regla, h["mensaje"])
