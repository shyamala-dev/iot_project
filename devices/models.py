from django.db import models
from django.contrib.auth.models import User

class Device(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('offline', 'Offline'),
        ('maintenance', 'Maintenance'),
    ]

    name = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='offline')

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='devices')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Session(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='sessions')
    start_time = models.DateTimeField(auto_now_add=True)
    energy_consumed = models.FloatField()