from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Device
from .permissions import IsOwner
from .serializers import DeviceSerializer

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def device_list(request):
    try:
        devices = Device.objects.filter(owner=request.user).select_related("owner")
        serializer = DeviceSerializer(devices, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

class DeviceListCreateView(generics.ListCreateAPIView):
    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Device.objects.filter(owner=self.request.user)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset.select_related("owner")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class DeviceDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated, IsOwner]

    def get_queryset(self):
        return Device.objects.filter(owner=self.request.user).select_related("owner")
