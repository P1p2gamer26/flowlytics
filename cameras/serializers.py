from rest_framework import serializers

from .models import Camera, CountingLine, Zone


class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = ("id", "name", "kind", "polygon")

    def validate_polygon(self, value):
        from django.core.exceptions import ValidationError as DjangoValidationError

        from .models import validate_polygon
        try:
            validate_polygon(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return value


class LineaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CountingLine
        fields = ("id", "name", "puntos", "invertir")

    def validate_puntos(self, value):
        from django.core.exceptions import ValidationError as DjangoValidationError

        from .models import validate_line
        try:
            validate_line(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return value


class CameraSerializer(serializers.ModelSerializer):
    zones = ZoneSerializer(many=True, read_only=True)
    lines = LineaSerializer(many=True, read_only=True)
    usuario = serializers.CharField(source="credencial_usuario", required=False,
                                    allow_blank=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Camera
        fields = ("id", "name", "source", "enabled", "es_video", "frame_w", "frame_h",
                  "descripcion", "contexto", "usuario", "password", "zones", "lines")
        read_only_fields = ("es_video", "frame_w", "frame_h")

    def create(self, validated_data):
        password = validated_data.pop("password", "")
        return self._con_credencial(super().create(validated_data), password)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", "")
        return self._con_credencial(super().update(instance, validated_data), password)

    @staticmethod
    def _con_credencial(camera, password):
        if password:
            camera.set_credencial(camera.credencial_usuario, password)
            camera.save(update_fields=["credencial_usuario", "credencial_cifrada"])
        return camera
