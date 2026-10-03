from django.core.management.base import BaseCommand

from analytics.models import EventClip, JobRun


class Command(BaseCommand):
    help = "Borra los clips de evento vencidos según CLIP_RETENTION_DAYS."

    def handle(self, *args, **opts):
        count = EventClip.purge_expired()
        JobRun.marcar("purge", detalle=f"{count} clips")
        self.stdout.write(self.style.SUCCESS(f"{count} clips vencidos eliminados."))
