from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Device, Session


@receiver(pre_save, sender=Device)
def normalize_serial_and_track_previous_status(sender, instance, **kwargs):
    if instance.serial_number:
        instance.serial_number = instance.serial_number.strip().upper()

    if instance.pk:
        instance._previous_status = (
            Device.objects.filter(pk=instance.pk).values_list("status", flat=True).first()
        )
    else:
        instance._previous_status = None


@receiver(post_save, sender=Device)
def create_session_when_activated(sender, instance, created, **kwargs):
    previous_status = getattr(instance, "_previous_status", None)
    became_active = instance.status == "active" and (created or previous_status != "active")

    if became_active:
        Session.objects.create(device=instance, energy_consumed=0.0)
