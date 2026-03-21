from django.core.management.base import BaseCommand

from devices.models import Device
from devices.rag import DeviceRAGService


class Command(BaseCommand):
    help = "Indexes device records into the local Chroma collection for RAG queries."

    def handle(self, *args, **options):
        queryset = Device.objects.select_related("owner").prefetch_related("sessions")
        service = DeviceRAGService()
        count = service.upsert_devices(queryset)
        self.stdout.write(
            self.style.SUCCESS(f"Indexed {count} devices into Chroma.")
        )