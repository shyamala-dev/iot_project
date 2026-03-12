from django.urls import path
from .views import (
    DeviceDetailView,
    DeviceListCreateView,
    device_list,
)

urlpatterns = [
    path('devices/list/', device_list, name='device-list'),
    path('devices/', DeviceListCreateView.as_view(), name='device-list-create'),
    path('devices/<int:pk>/', DeviceDetailView.as_view(), name='device-detail'),
]
