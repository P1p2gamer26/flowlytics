"""Vistas de descarga del reporte por periodo. Delgadas: resuelven el business
(vía business_or_403), leen el rango de fechas y delegan en reporte_periodo.
CSV con la stdlib; PDF con matplotlib (Tarea 3).
"""
import csv
import io
from datetime import date, timedelta

import matplotlib
matplotlib.use("Agg")                 # sin display: corre en CI headless
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from django.contrib.auth.decorators import login_required
from django.core.exceptions import SuspiciousOperation
from django.http import HttpResponse

from tenancy.permissions import business_or_403

from .reportes import reporte_periodo

COLUMNAS = ["fecha", "visitantes", "entradas", "salidas",
            "aforo_pico", "hora_pico", "cola_seg_prom"]

RANGO_MAX_DIAS = 366


def _rango(request):
    """Lee desde/hasta del querystring; por defecto los últimos 7 días."""
    hasta = request.GET.get("hasta")
    desde = request.GET.get("desde")
    try:
        hasta = date.fromisoformat(hasta) if hasta else date.today()
        desde = date.fromisoformat(desde) if desde else hasta - timedelta(days=6)
    except ValueError:
        raise SuspiciousOperation("Fecha invalida, use YYYY-MM-DD")
    if desde > hasta or (hasta - desde).days >= RANGO_MAX_DIAS:
        raise SuspiciousOperation(f"Rango invalido (maximo {RANGO_MAX_DIAS} dias)")
    return desde, hasta


@login_required
def reporte_csv(request):
    business = business_or_403(request.user, request.GET.get("business"))
    desde, hasta = _rango(request)
    filas = reporte_periodo(business, desde, hasta)

    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = (
        f'attachment; filename="reporte-{business.pk}-{desde}-a-{hasta}.csv"')
    escritor = csv.DictWriter(resp, fieldnames=COLUMNAS)
    escritor.writeheader()
    escritor.writerows(filas)
    return resp


@login_required
def reporte_pdf(request):
    business = business_or_403(request.user, request.GET.get("business"))
    desde, hasta = _rango(request)
    filas = reporte_periodo(business, desde, hasta)

    buffer = io.BytesIO()
    with PdfPages(buffer) as pdf:
        fig, (ax_tabla, ax_grafico) = plt.subplots(
            2, 1, figsize=(8.27, 11.69), gridspec_kw={"height_ratios": [2, 1]})
        fig.suptitle(f"Reporte de {business.name}\n{desde} a {hasta}", fontsize=14)

        ax_tabla.axis("off")
        celdas = [[f[c] if f[c] is not None else "—" for c in COLUMNAS] for f in filas]
        tabla = ax_tabla.table(cellText=celdas, colLabels=COLUMNAS, loc="upper center")
        tabla.auto_set_font_size(False)
        tabla.set_fontsize(8)

        ax_grafico.bar([f["fecha"] for f in filas], [f["visitantes"] for f in filas])
        ax_grafico.set_ylabel("Visitantes")
        ax_grafico.tick_params(axis="x", rotation=45, labelsize=7)

        fig.tight_layout(rect=[0, 0, 1, 0.96])
        pdf.savefig(fig)
        plt.close(fig)

    resp = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    resp["Content-Disposition"] = (
        f'attachment; filename="reporte-{business.pk}-{desde}-a-{hasta}.pdf"')
    return resp
