from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from cameras.models import Camera
from .forms import AceptarInvitacionForm, InvitarForm, RegistroForm
from .models import Business, Invitation, Profile
from .permissions import business_or_403
from .rubros import perfil

BACKEND = "tenancy.lockout.LockoutModelBackend"


def registrar(request):
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            datos = form.cleaned_data
            with transaction.atomic():
                user = User.objects.create_user(
                    username=datos["username"], password=datos["password"])
                biz = Business.objects.create(
                    name=datos["nombre_negocio"], kind=datos["kind"])
                Profile.objects.create(user=user, role="owner", business=biz)
            login(request, user, backend=BACKEND)
            return redirect("onboarding")
    else:
        form = RegistroForm()
    return render(request, "tenancy/registro.html", {"form": form})


@login_required
def onboarding(request):
    business = Business.objects.for_user(request.user).first()
    camaras = Camera.objects.filter(business=business) if business else Camera.objects.none()
    tiene_camara = camaras.exists()
    tiene_zona = any(c.zones.exists() for c in camaras)
    return render(request, "tenancy/onboarding.html", {
        "business": business,
        "rubro": perfil(business.kind) if business else None,
        "tiene_camara": tiene_camara,
        "tiene_zona": tiene_zona,
        "completo": tiene_camara and tiene_zona,
    })


@login_required
def invitar(request):
    business = Business.objects.for_user(request.user).first()
    if business is None:
        raise PermissionDenied("No tienes un negocio al que invitar.")
    # aislamiento: solo se invita al negocio propio, verificado por el punto único
    business_or_403(request.user, business.pk)

    if request.method == "POST":
        form = InvitarForm(request.POST)
        if form.is_valid():
            inv = Invitation.objects.create(business=business, email=form.cleaned_data["email"])
            enlace = request.build_absolute_uri(f"/invitacion/{inv.token}/")
            return render(request, "tenancy/invitar.html",
                          {"form": InvitarForm(), "enlace": enlace})
    else:
        form = InvitarForm()
    return render(request, "tenancy/invitar.html", {"form": form})


def aceptar_invitacion(request, token):
    inv = get_object_or_404(Invitation, token=token, aceptada=False)
    if request.method == "POST":
        form = AceptarInvitacionForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = User.objects.create_user(
                    username=form.cleaned_data["username"],
                    password=form.cleaned_data["password"])
                Profile.objects.create(user=user, role=inv.role, business=inv.business)
                inv.aceptada = True
                inv.save(update_fields=["aceptada"])
            login(request, user, backend=BACKEND)
            return redirect("home")
    else:
        form = AceptarInvitacionForm()
    return render(request, "tenancy/aceptar_invitacion.html", {"form": form, "inv": inv})


@login_required
def plataforma(request):
    perfil = getattr(request.user, "profile", None)
    if perfil is None or not perfil.is_admin:
        raise PermissionDenied("Solo administradores de la plataforma.")

    negocios = Business.objects.select_related("plan").annotate(
        num_camaras=Count("cameras", distinct=True),
        num_miembros=Count("members", distinct=True),
    )
    filas = [{
        "business": b,
        "plan": b.plan.nombre if b.plan_id else "(sin plan)",
        "num_camaras": b.num_camaras,
        "num_miembros": b.num_miembros,
        "max_camaras": b.max_camaras,
    } for b in negocios]
    return render(request, "tenancy/plataforma.html", {"filas": filas})
