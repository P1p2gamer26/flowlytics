"""Siembra reglas y entregas de demostración para los negocios demo."""
from django.core.management.base import BaseCommand

from tenancy.models import Business

from analytics.avisos_demo import sembrar_avisos


class Command(BaseCommand):
    help = "Siembra avisos de demo para 'Demo' y 'Tiendas grabadas (demo)'."

    def handle(self, *args, **opts):
        for nombre in ["Demo", "Tiendas grabadas (demo)"]:
            biz = Business.objects.filter(name=nombre).first()
            if biz:
                sembrar_avisos(biz)
                self.stdout.write(self.style.SUCCESS(f"Avisos sembrados para '{biz.name}'"))
            else:
                self.stdout.write(self.style.WARNING(f"Negocio '{nombre}' no encontrado, se omite."))