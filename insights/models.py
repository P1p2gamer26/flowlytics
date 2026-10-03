from django.db import models

from tenancy.models import Business


class Insight(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="insights")
    day = models.DateField()
    body = models.TextField()
    model = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("business", "day")
        ordering = ["-day"]

    def __str__(self):
        return f"{self.business.name} — {self.day}"


# Este modelo NUNCA guarda business.pk, track_id, Recorrido.pistas
# ni ningún dato que permita identificar al negocio o a una persona.
class CorpusEntry(models.Model):
    """Métricas anónimas de un negocio-día, para comparación entre pares.

    A propósito NO tiene relación con Business: la huella es un hash no
    reversible que solo sirve para excluir a un negocio de su propia cohorte.
    """
    cohorte = models.CharField(max_length=20, db_index=True,
                               help_text="Tipo de negocio: cafe, restaurant, retail...")
    huella = models.CharField(max_length=16, db_index=True)
    day = models.DateField()

    visitantes = models.IntegerField()
    aforo_pico = models.IntegerField()
    espera_fila_seg = models.FloatField(null=True, blank=True)
    cobertura_personal = models.FloatField(null=True, blank=True)
    hora_pico = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ("huella", "day")
        indexes = [models.Index(fields=["cohorte", "day"])]

    def __str__(self):
        return f"{self.cohorte} / {self.day}"
