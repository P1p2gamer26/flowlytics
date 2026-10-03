import hashlib
import json
import tarfile
import os
import tempfile
from datetime import datetime
from django.core.management.base import BaseCommand
from analytics.models import Event, MetricWindow, EventClip


class Command(BaseCommand):
    help = "Exporta respaldo comprimido con manifiesto de integridad"

    def handle(self, *args, **options):
        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        backup_dir = "backups"
        os.makedirs(backup_dir, exist_ok=True)
        manifest_path = os.path.join(backup_dir, f"manifiesto_{ts}.json")
        tar_path = os.path.join(backup_dir, f"respaldo_{ts}.tar.gz")

        files_to_backup = ["db.sqlite3", ".env"]
        for root_dir in ["docs", "demo"]:
            if os.path.exists(root_dir):
                files_to_backup.append(root_dir)
        if os.path.exists("media/clips"):
            files_to_backup.append("media/clips")

        manifest = {}
        for f in files_to_backup:
            if not os.path.exists(f):
                manifest[f] = "missing"
                continue
            if os.path.isfile(f):
                sha256 = hashlib.sha256()
                with open(f, "rb") as file:
                    for chunk in iter(lambda: file.read(4096), b""):
                        sha256.update(chunk)
                manifest[f] = sha256.hexdigest()
            elif os.path.isdir(f):
                for root, dirs, files in os.walk(f):
                    for file in files:
                        archivo_ruta = os.path.join(root, file)
                        archivo_rel = os.path.join(f, file)
                        sha256 = hashlib.sha256()
                        with open(archivo_ruta, "rb") as archivo:
                            for chunk in iter(lambda: archivo.read(4096), b""):
                                sha256.update(chunk)
                        manifest[archivo_rel] = sha256.hexdigest()

        manifest["conteos"] = {
            "Event": Event.objects.count(),
            "MetricWindow": MetricWindow.objects.count(),
            "EventClip": EventClip.objects.count(),
        }
        manifest["fecha"] = ts

        import sqlite3
        db_path = "db.sqlite3"
        page_checksums = []
        page_size = 4096
        page_count = 0
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA page_size")
            row = cursor.fetchone()
            page_size = row[0] if row and row[0] else 4096
            cursor.execute("PRAGMA page_count")
            row = cursor.fetchone()
            page_count = row[0] if row and row[0] else 0
            conn.close()
            with open(db_path, "rb") as f:
                for _ in range(page_count):
                    page_data = f.read(page_size)
                    if not page_data:
                        break
                    sha256 = hashlib.sha256(page_data).hexdigest()
                    page_checksums.append(sha256)
        manifest["page_checksums"] = page_checksums
        manifest["page_size"] = page_size
        manifest["page_count"] = page_count

        with open(manifest_path, "w") as mf:
            json.dump(manifest, mf, indent=2)

        with tarfile.open(tar_path, "w:gz") as tar:
            for f in files_to_backup:
                if os.path.exists(f):
                    tar.add(f, arcname=f)
            tar.add(manifest_path, arcname=os.path.basename(manifest_path))

        self.stdout.write(f"Respaldo creado: {tar_path}")
        self.stdout.write(f"Manifiesto: {manifest_path}")
        self.stdout.write(f"Conteos: {manifest['conteos']}")