import tarfile, tempfile, json, hashlib, os, shutil
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Restaura respaldo y verifica integridad"

    def add_arguments(self, parser):
        parser.add_argument("archivo", type=str, help="Ruta al .tar.gz")

    def handle(self, *args, **options):
        archivo = options["archivo"]
        if not os.path.exists(archivo):
            self.stderr.write(f"Archivo no encontrado: {archivo}")
            raise SystemExit(1)

        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(archivo, "r:gz") as tar:
                tar.extractall(path=tmpdir)

            manifest_path = None
            for root, dirs, files in os.walk(tmpdir):
                for f in files:
                    if f.startswith("manifiesto") and f.endswith(".json"):
                        manifest_path = os.path.join(root, f)
                        break
                if manifest_path:
                    break

            if not manifest_path:
                self.stderr.write("Manifiesto no encontrado en respaldo")
                raise SystemExit(1)

            with open(manifest_path) as mf:
                manifest = json.load(mf)

            # Verificar checksums de archivos extraídos
            for f in ["db.sqlite3", ".env", "media/clips"]:
                ruta = os.path.join(tmpdir, f)
                if f not in manifest or manifest[f] == "missing":
                    continue
                if not os.path.exists(ruta):
                    self.stdout.write(f"Advertencia: {f} no presente en respaldo")
                    continue
                sha256 = hashlib.sha256()
                if os.path.isfile(ruta):
                    with open(ruta, "rb") as file:
                        for chunk in iter(lambda: file.read(4096), b""):
                            sha256.update(chunk)
                if sha256.hexdigest() != manifest[f]:
                    self.stderr.write(f"Checksum fallido para {f}")
                    raise SystemExit(1)

            # Restaurar db.sqlite3 a una copia temporal
            db_origen = os.path.join(tmpdir, "db.sqlite3")
            db_destino = "db_restaurada.sqlite3"
            if os.path.exists(db_origen):
                shutil.copy(db_origen, db_destino)

            self.stdout.write("Integridad verificada: OK")
            self.stdout.write(f"Base restaurada: {db_destino}")
            self.stdout.write(f"Manifiesto: {manifest_path}")
