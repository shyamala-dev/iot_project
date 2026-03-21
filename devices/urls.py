from django.urls import path
from .views import (
    DeviceDetailView,
    DeviceListCreateView,
    device_list,
    rag_playground,
    rag_query,
)

urlpatterns = [
    path('rag/', rag_playground, name='rag-playground'),
    path('devices/list/', device_list, name='device-list'),
    path('devices/', DeviceListCreateView.as_view(), name='device-list-create'),
    path('devices/<int:pk>/', DeviceDetailView.as_view(), name='device-detail'),
    path('devices/rag/query/', rag_query, name='device-rag-query'),
]
