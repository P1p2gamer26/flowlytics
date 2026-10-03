# Re-export para que los tests puedan importar Recorrido como vision.models.Recorrido
from cameras.models import Recorrido  # noqa: F401

import django.db.models as models

class ResumenDia(models.Model):
    camera = models.ForeignKey("cameras.Camera", on_delete=models.CASCADE, null=True)
    dia = models.DateField(auto_now_add=True)
    total_visitors = models.IntegerField(default=0)
    metrica_principal = models.CharField(max_length=80, blank=True, default="")
    valor = models.FloatField(default=0.0)
    negocio = models.CharField(max_length=80, blank=True, default="")

    class Meta:
        db_table = "resumen_dia"
