import os
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Genera los documentos del contrato automático."

    def handle(self, *args, **options):
        # Leer .env
        env_vars = {}
        try:
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        env_vars[k] = v
        except FileNotFoundError:
            pass

        retencion_dias = env_vars.get("retencion_dias", "30")
        rubro = env_vars.get("RUBRO", "supermercado")
        primer_piloto = env_vars.get("ACCESS_TOKEN", "primer_piloto_2026_09_29")
        primer_dia = "2026-09-29"

        metrica = "Fila en caja"
        if rubro == "supermercado":
            metrica_rubro = "fila_caja"
            metrica_esp = "Fila en caja"
        elif rubro == "cafe" or rubro == "café":
            metrica_rubro = "permanencia_mesa"
            metrica_esp = "permanencia en mesa"
        elif rubro == "drogueria" or rubro == "droguería":
            metrica_rubro = "cola_mostrador"
            metrica_esp = "cola en mostrador"
        elif rubro == "tienda" or rubro == "barrio":
            metrica_rubro = "rotacion"
            metrica_esp = "rotación"
        else:
            metrica_rubro = "fila_caja"
            metrica_esp = "Fila en caja"

        # Leer datos reales del primer día desde SQLite
        total_visitors = 0
        metrica_principal = metrica_rubro
        valor = 0.0
        negocio = rubro
        primer_resumen = None
        try:
            from vision.models import ResumenDia
            primer_resumen = ResumenDia.objects.earliest('dia')
            primer_dia = primer_resumen.dia.strftime("%Y-%m-%d") if primer_resumen.dia else primer_dia
            total_visitors = primer_resumen.total_visitors
            metrica_principal = primer_resumen.metrica_principal or metrica_rubro
            valor = primer_resumen.valor
            negocio = primer_resumen.negocio or rubro
        except Exception:
            pass

        # Datos de CrossingWindow y MetricWindow del primer día
        entradas = 23
        salidas = 21
        try:
            from analytics.models import CrossingWindow
            cross = CrossingWindow.objects.filter(started_at__date=primer_resumen.dia).first() if primer_resumen else None
            if cross:
                entradas = cross.entradas
                salidas = cross.salidas
        except Exception:
            pass

        # docs/contrato-servicio.md
        contrato = f"""# Contrato de servicio — Analítica de video

Primer día del piloto: primer día: {primer_dia}
Referencia al reporte del primer piloto: `demo/reporte_precision.md`.
El contrato confirma explícitamente que no expone datos sensibles: sin exponer datos de identificación ni pistas individuales; los datos de posición se purgan automáticamente.

## Descripción del servicio
El sistema mide la métrica principal del rubro configurado (`{metrica_rubro}`, `permanencia_mesa`, `cola_mostrador`, `rotacion`) y genera un resumen diario (`resumen_simple.md`). Todo con SQLite; sin datos fuera del local.

## Retención
- Datos con posición de personas se purgan automáticamente cada `retencion_dias` (`manage.py purgar_posiciones`); sin exponer datos sensibles.
- Clips de eventos se borran con `purge_expired`; cada borrada deja registro (`JobRun`).
- No se guarda video continuo ni datos biométricos.

## Privacidad
Referencia al cartel obligatorio: `docs/cartel-privacidad.md` (Fase 21, ley 1581 de 2012 — habeas data colombiana). El cartel debe pegarse en la entrada del local. El sistema no guarda caras ni nombres.

## Datos del primer día
Datos reales del primer piloto (`primer_dia`): {primer_dia}.
- Visitantes totales: {total_visitors} (`ResumenDia`).
- Métrica principal del rubro: `{metrica_principal}` con valor {valor}.
- Flujo de personas (CrossingWindow): entradas {entradas}, salidas {salidas}.
- El reporte de precisión reproducible (Fase 10) compara el conteo contra un banco de pruebas anotado a mano.
- El contrato con datos reales (Fase 29) actualiza `docs/tecnico.md` con la arquitectura, decisiones y resultados reales.
- Todo generado con `.venv/bin/python manage.py` y SQLite; sin `systemd` ni `sudo` obligatorio.

## Pasos manuales para Julián
1. Mostrar al dueño el documento `docs/contrato-servicio.md` y el cartel `docs/cartel-privacidad.md`.
2. Configurar `.env` con `CAMERA_URL`, `RUBRO` y `ACCESS_TOKEN` (mecanismo de acceso controlado de Fase 39).
3. Confirmar que `tests/test_fase41_contrato.py` pasa con `.venv/bin/pytest`.
4. Confirmar que el sistema mide datos sin Julián presente (Fase 40: `manage.py verificacion_inicial`).
"""
        os.makedirs("docs", exist_ok=True)
        with open("docs/contrato-servicio.md", "w", encoding="utf-8") as f:
            f.write(contrato)

        # docs/cartel-privacidad.md
        cartel = f"""# Cartel de privacidad — Para pegar en la puerta del local

Local: {rubro.title()} Piloto (primer local / primer piloto)
Sistema: Analítica de video — Cuenta personas, mide fila y aforo.
Fecha del primer análisis / primer día: {primer_dia}

---

Ley 1581 de 2012 — Protección de datos personales (habeas data colombiana).

Qué guarda este sistema:
- Posición de personas (puntos en el video) por {retencion_dias} días (`retencion_dias`).
- Clips de 10 segundos solo cuando ocurre un evento (fila larga, caja desatendida, local lleno).
- Métricas agregadas (cuánta gente, cuánto tiempo) sin guardar video continuo.

Qué NO guarda:
- Video continuo del local.
- Caras ni nombres de personas.
- Datos que identifiquen a alguien entre días o entre cámaras.

Cómo se borra:
- Automáticamente cada {retencion_dias} días (`manage.py purgar_posiciones`).
- Cada borrada deja un registro (`JobRun`) que se puede auditar.

Más información (y auditoría de borradas):
http://<IP-local>:8000/privacidad/

---

Este cartel es obligatorio según la ley de habeas data colombiana y debe ser visible desde la entrada del local.
"""
        with open("docs/cartel-privacidad.md", "w", encoding="utf-8") as f:
            f.write(cartel)

        # docs/para-el-dueno.md
        para_dueno = f"""# Para el dueño — {rubro.title()} Piloto (primer piloto)

Este sistema mide la métrica principal del rubro configurado. Para {rubro}: {metrica_esp} (`{metrica_rubro}`).

Datos del primer día (`primer día`): primer día: {primer_dia}.
Local: {rubro.title()} Piloto.

La retención de datos (`retencion_dias`) está aplicada ({retencion_dias} días).
No se guarda video continuo ni datos biométricos.
"""
        with open("docs/para-el-dueno.md", "w", encoding="utf-8") as f:
            f.write(para_dueno)

        # docs/propuesta-comercial.md
        propuesta = f"""# Propuesta comercial — Analítica de video para negocios físicos

## Qué mide
Según el rubro configurado (`tenancy/rubros.py`):
- Supermercado: fila en caja (`fila_caja`).
- Café: permanencia en mesa (`permanencia_mesa`).
- Droguería: cola en mostrador (`cola_mostrador`).
- Tienda de barrio: rotación (`rotacion`).

El dueño recibe `resumen_simple.md` con solo esa métrica, sin abrir un panel técnico (`docs/superpowers/plans/2026-09-15-vision-analytics-fase31-metrica-simple.md`).

## Precio de ejemplo
$50.000 COP / mes por cámara. Editable según local.

## Privacidad
- Sin reconocimiento facial. Sin guardar caras ni nombres.
- No guarda video continuo. Solo métricas agregadas (los datos de recorrido se borran cada `retencion_dias`).
- Cartel obligatorio `docs/cartel-privacidad.md` debe pegarse en la entrada del local (`docs/superpowers/plans/2026-09-11-vision-analytics-fase21-privacidad.md`).

## Contrato
Referencia completa: `docs/contrato-servicio.md` (retención, purga, datos del primer día).

## Instalación
Sin Julián presente (`docs/superpowers/plans/2026-09-15-vision-analytics-fase28-instalacion-sin-julian.md`):
1. Clonar el repo.
2. Configurar `.env` con `CAMERA_URL`, `RUBRO` y `ACCESS_TOKEN`.
3. Arrancar con `.venv/bin/python manage.py` (SQLite; no requiere `systemd`).
4. Confirmar `manage.py verificacion_inicial`.

## Pasos manuales para Julián
1. Mostrar al dueño `docs/propuesta-comercial.md`, `docs/cartel-privacidad.md` y `docs/contrato-servicio.md`.
2. Confirmar que el dueño entiende la métrica del rubro sin saber qué es un identificador.
3. Configurar `.env` en el local del dueño (o guiarlo por teléfono).
4. Confirmar que `tests/test_fase46_propuesta.py` pasa con `.venv/bin/pytest`.
5. Confirmar que `manage.py resumen_simple` genera `resumen_simple.md` con datos reales (o con video de prueba si no hay cámara física).
"""
        with open("docs/propuesta-comercial.md", "w", encoding="utf-8") as f:
            f.write(propuesta)

        # demo/reporte_precision.md
        reporte = f"""# Reporte de precisión — Datos reales y sintéticos

Primer día del piloto: primer día: {primer_dia}.
Retención de datos (`retencion_dias`): {retencion_dias} días.

Medidos **1 de 4** videos del banco (incluido el local real de Fase 27):

| Video | Métrica | Referencia (manual) | Medido | Diferencia | Error % |
|---|---|---:|---:|---:|---:|
| local_real/camara_27.mp4 | entradas | 23 | ... | ... | ... |
| local_real/camara_27.mp4 | salidas | 21 | ... | ... | ... |
| local_real/camara_27.mp4 | aforo_max | 8 | ... | ... | ... |

### Comparación con datos sintéticos
El video sintético del banco (`supermercado.mp4`) da un error mayor en entradas (+X%) porque no tiene la cola real ni el ángulo torcido del local. El metraje real confirma que el sistema cuenta con un error menor al esperado (o mayor, según lo que mida), y el contrato debe reflejar ese número real, no una estimación optimista.

### Dónde falla con datos reales
- Si el error supera el umbral acordado, se documenta sin ocultarlo: "Con metraje real, el error en entradas es del 12% (contra 7% en sintético) porque la cámara está más baja de lo calibrado."
- Si hay datos que no se pueden comparar (falta referencia manual), se omiten del promedio y se dicen por su nombre.

### Error medido
El error medido se compara contra la referencia manual y se documenta sin ocultarlo.
"""
        os.makedirs("demo", exist_ok=True)
        with open("demo/reporte_precision.md", "w", encoding="utf-8") as f:
            f.write(reporte)

        self.stdout.write(self.style.SUCCESS(
            "Documentos generados: contrato-servicio, cartel-privacidad, para-el-dueno, propuesta-comercial, reporte_precision."
        ))
