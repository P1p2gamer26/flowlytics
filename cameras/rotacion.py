"""Re-cifra las credenciales de cámara de una clave a otra en una transacción.

Rotar SECRET_KEY sin esto borra en silencio todas las credenciales RTSP. Correr
`rotar_clave` ANTES de cambiar el secreto en .env.
"""
from cryptography.fernet import Fernet
from django.db import transaction


def rotar(cameras, clave_vieja, clave_nueva):
    f_vieja, f_nueva = Fernet(clave_vieja), Fernet(clave_nueva)
    with transaction.atomic():
        for cam in cameras:
            if not cam.credencial_cifrada:
                continue
            plano = f_vieja.decrypt(bytes(cam.credencial_cifrada))
            cam.credencial_cifrada = f_nueva.encrypt(plano)
            cam.save(update_fields=["credencial_cifrada"])
