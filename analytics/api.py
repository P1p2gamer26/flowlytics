from datetime import date

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from cameras.models import CameraHealth
from insights.corpus import comparativa as calcular_comparativa
from insights.models import Insight
from tenancy.permissions import business_or_403
from tenancy.rubros import perfil

from .aggregates import daily_summary, hoy_del_negocio
from .models import AlertRule, AlertDelivery, Event
from .avisos import umbrales_de


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def summary_view(request):
    business = business_or_403(request.user, request.query_params.get("business"))
    day = request.query_params.get("date")
    day = date.fromisoformat(day) if day else hoy_del_negocio(business)
    # El rubro lo añade la vista, no `daily_summary`: ese diccionario lo leen
    # también el corpus anónimo, los reportes y el humo.
    return Response({**daily_summary(business, day), "rubro": perfil(business.kind)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def negocio_actual_view(request):
    from tenancy.models import Business

    visibles = list(Business.objects.for_user(request.user))
    if not visibles:
        return Response({"error": "Tu cuenta no tiene un negocio asignado."}, status=404)
    return Response({
        "business_id": visibles[0].pk,
        "nombre": visibles[0].name,
        "negocios": [{"id": b.pk, "nombre": b.name} for b in visibles],
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def events_view(request):
    business = business_or_403(request.user, request.query_params.get("business"))
    events = Event.objects.filter(camera__business=business).select_related("camera")[:50]
    return Response([
        {"id": e.pk, "kind": e.kind, "camera": e.camera.name, "zone": e.zone_name,
         "value": e.value, "occurred_at": e.occurred_at.isoformat(),
         "has_clip": hasattr(e, "clip")}
        for e in events
    ])


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def panel_extra_view(request):
    """Lo que el panel muestra además del resumen: avisos de cámaras sin señal,
    comparativa contra la cohorte y la recomendación del día.

    Van juntos en un endpoint porque el panel los pinta en la misma pantalla y
    ninguno justifica su propia ronda de red.
    """
    business = business_or_403(request.user, request.query_params.get("business"))
    day = request.query_params.get("date")
    day = date.fromisoformat(day) if day else hoy_del_negocio(business)
    insight = Insight.objects.filter(business=business, day=day).first()

    return Response({
        "camaras_caidas": [
            {"camara": s.camera.name,
             "ultimo_latido": s.ultimo_latido.isoformat(),
             "ultimo_error": s.ultimo_error}
            for s in CameraHealth.objects.caidas(business).select_related("camera")
        ],
        "comparativa": calcular_comparativa(business, day),
        "recomendacion": insight.body if insight else "",
    })


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def avisos_view(request):
    """Reglas de aviso del negocio: listar y crear.
    GET -> {reglas, sugeridos, horario, recientes}
    POST -> crea regla (valida choices, destino obligatorio) -> 201
    """
    business = business_or_403(request.user, request.query_params.get("business") or request.data.get("business"))

    if request.method == "GET":
        reglas = AlertRule.objects.filter(business=business).order_by("tipo_evento")
        datos_reglas = [{
            "id": r.pk,
            "tipo_evento": r.tipo_evento,
            "umbral": r.umbral,
            "canal": r.canal,
            "destino": r.destino,
            "minutos_silencio": r.minutos_silencio,
            "activa": r.activa,
        } for r in reglas]

        sugeridos = umbrales_de(business)

        horario = {"abre": business.abre.strftime("%H:%M") if business.abre else "00:00",
                   "cierra": business.cierra.strftime("%H:%M") if business.cierra else "00:00"}

        recientes = AlertDelivery.objects.filter(rule__business=business).select_related("rule")[:20]
        datos_recientes = [{
            "tipo": d.rule.tipo_evento,
            "mensaje": d.mensaje,
            "resultado": d.resultado,
            "cuando": d.creado.isoformat(),
        } for d in recientes]

        return Response({"reglas": datos_reglas, "sugeridos": sugeridos, "horario": horario, "recientes": datos_recientes})

    # POST
    tipo_evento = request.data.get("tipo_evento")
    canal = request.data.get("canal")
    destino = (request.data.get("destino") or "").strip()
    umbral = request.data.get("umbral")
    minutos_silencio = request.data.get("minutos_silencio", 15)

    if tipo_evento not in dict(AlertRule._meta.get_field("tipo_evento").choices):
        return Response({"error": "tipo_evento inválido"}, status=400)
    if canal not in dict(AlertRule._meta.get_field("canal").choices):
        return Response({"error": "canal inválido"}, status=400)
    if not destino:
        return Response({"error": "destino es obligatorio"}, status=400)

    if umbral is not None:
        try:
            umbral = float(umbral)
        except (TypeError, ValueError):
            return Response({"error": "umbral debe ser numérico"}, status=400)

    try:
        minutos_silencio = int(minutos_silencio)
    except (TypeError, ValueError):
        return Response({"error": "minutos_silencio debe ser entero"}, status=400)

    regla = AlertRule.objects.create(
        business=business,
        tipo_evento=tipo_evento,
        canal=canal,
        destino=destino,
        umbral=umbral,
        minutos_silencio=minutos_silencio,
        activa=True,
    )
    return Response({
        "id": regla.pk,
        "tipo_evento": regla.tipo_evento,
        "umbral": regla.umbral,
        "canal": regla.canal,
        "destino": regla.destino,
        "minutos_silencio": regla.minutos_silencio,
        "activa": regla.activa,
    }, status=201)


@api_view(["PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def aviso_detalle_view(request, regla_id):
    """Actualización parcial (activa, umbral, destino, minutos_silencio, canal) o borrado."""
    business = business_or_403(request.user, request.query_params.get("business") or request.data.get("business"))
    regla = AlertRule.objects.filter(pk=regla_id, business=business).first()
    if regla is None:
        return Response({"error": "No existe ese aviso."}, status=404)

    if request.method == "DELETE":
        regla.delete()
        return Response(status=204)

    # PUT - actualización parcial
    data = request.data
    if "activa" in data:
        # Un formulario manda "False" como texto, y bool("False") es True.
        regla.activa = data["activa"] in (True, 1, "1", "true", "True")
    if "umbral" in data and data["umbral"] is not None:
        try:
            regla.umbral = float(data["umbral"])
        except (TypeError, ValueError):
            return Response({"error": "umbral debe ser numérico"}, status=400)
    elif "umbral" in data and data["umbral"] is None:
        regla.umbral = None
    if "destino" in data:
        destino = (data["destino"] or "").strip()
        if not destino:
            return Response({"error": "destino no puede estar vacío"}, status=400)
        regla.destino = destino
    if "minutos_silencio" in data:
        try:
            regla.minutos_silencio = int(data["minutos_silencio"])
        except (TypeError, ValueError):
            return Response({"error": "minutos_silencio debe ser entero"}, status=400)
    if "canal" in data:
        if data["canal"] not in dict(AlertRule._meta.get_field("canal").choices):
            return Response({"error": "canal inválido"}, status=400)
        regla.canal = data["canal"]

    regla.save()
    return Response({
        "id": regla.pk,
        "tipo_evento": regla.tipo_evento,
        "umbral": regla.umbral,
        "canal": regla.canal,
        "destino": regla.destino,
        "minutos_silencio": regla.minutos_silencio,
        "activa": regla.activa,
    })


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def aviso_horario_view(request):
    """Guarda horario de avisos en Business: {abre: 'HH:MM', cierra: 'HH:MM'}."""
    business = business_or_403(request.user, request.query_params.get("business") or request.data.get("business"))
    abre = request.data.get("abre")
    cierra = request.data.get("cierra")

    if abre is None or cierra is None:
        return Response({"error": "abre y cierra son obligatorios"}, status=400)

    from datetime import datetime
    for campo, valor in (("abre", abre), ("cierra", cierra)):
        try:
            if len(valor) != 5:
                raise ValueError
            setattr(business, campo, datetime.strptime(valor, "%H:%M").time())
        except (TypeError, ValueError):
            return Response({"error": f"{campo} debe tener formato HH:MM"}, status=400)

    business.save(update_fields=["abre", "cierra"])
    return Response({"abre": business.abre.strftime("%H:%M"), "cierra": business.cierra.strftime("%H:%M")})
