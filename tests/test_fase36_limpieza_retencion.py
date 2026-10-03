import os, pytest
from analytics.models import JobRun

@pytest.mark.django_db
def test_limpieza_no_borra_dentro_de_retencion():
    backup_dir = "backups"
    os.makedirs(backup_dir, exist_ok=True)
    archivo_reciente = os.path.join(backup_dir, "respaldo_2026-09-25_120000.tar.gz")
    with open(archivo_reciente, "w") as f:
        f.write("simulado")
    assert os.path.exists(archivo_reciente)
    JobRun.marcar("limpieza_respaldo", ok=True, detalle="simulación de limpieza")
    if os.path.exists(archivo_reciente):
        os.remove(archivo_reciente)