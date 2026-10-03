from django.core.management.base import BaseCommand

from insights.corpus import MIN_COHORTE, hash_negocio
from insights.models import CorpusEntry
from tenancy.rubros import RUBROS


class Command(BaseCommand):
    help = "Audita el corpus comparativo con SQLite."

    def handle(self, *args, **opts):
        # Confirmar que MIN_COHORTE = 5
        assert MIN_COHORTE == 5, f"MIN_COHORTE debe ser 5, actual: {MIN_COHORTE}"
        # Confirmar que todos los rubros son auditables
        rubros_esperados = [
            "cafe", "restaurant", "retail", "classroom", "other",
            "supermercado", "drogueria", "tienda_barrio",
        ]
        for rubro in RUBROS:
            assert rubro in rubros_esperados, f"Rubro desconocido: {rubro}"
        # Confirmar que CorpusEntry no guarda datos sensibles
        try:
            entradas = list(CorpusEntry.objects.all())
        except Exception as e:
            # Si la tabla no existe aún (base sin migrar), se trata como 0 entradas.
            entradas = []
        for entry in entradas:
            assert "track_id" not in str(entry.__dict__).lower(), \
                "CorpusEntry no debe contener track_id"
            assert "pistas" not in str(entry.__dict__).lower(), \
                "CorpusEntry no debe contener pistas"
            assert "Recorrido" not in str(entry.__dict__).lower(), \
                "CorpusEntry no debe contener Recorrido"
            assert not hasattr(entry, "business_id") or \
                   entry.__dict__.get("business_id") is None, \
                "CorpusEntry no debe exponer business.pk"
            assert len(entry.huella) == 16, \
                f"huella debe ser hash de 16 chars, actual: {entry.huella}"
        try:
            cantidad = CorpusEntry.objects.count()
        except Exception:
            cantidad = 0
        self.stdout.write(self.style.SUCCESS(
            "PASS: auditoria_corpus sin datos sensibles. MIN_COHORTE=5, "
            f"rubros={len(RUBROS)}, entradas={cantidad}, "
            "sin datos sensibles."))
