from rest_framework import serializers
from .models import Device


class DeviceSerializer(serializers.ModelSerializer):
    def validate_serial_number(self, value):
        normalized_serial = value.strip().upper()
        queryset = Device.objects.filter(serial_number=normalized_serial)

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "A device with this s erial number already exists."
            )

        return normalized_serial

    class Meta:
        model = Device
        fields = '__all__'
        read_only_fields = ['owner', 'created_at']
