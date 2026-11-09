from rest_framework import serializers

from .models import Stamp


class StampSerializer(serializers.ModelSerializer[Stamp]):
    class Meta:
        model = Stamp
        fields = ["code", "number", "name", "description"]
        read_only_fields = fields
