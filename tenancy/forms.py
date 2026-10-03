from django import forms
from django.contrib.auth.models import User

from .models import BUSINESS_KINDS


class RegistroForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    nombre_negocio = forms.CharField(max_length=120)
    kind = forms.ChoiceField(choices=BUSINESS_KINDS)

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ese usuario ya existe.")
        return username


class InvitarForm(forms.Form):
    email = forms.EmailField(required=False)


class AceptarInvitacionForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ese usuario ya existe.")
        return username
