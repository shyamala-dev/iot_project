from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Device
from .rag import DeviceRAGService
from .mcp_server import get_device_tool, list_devices_tool


class DeviceRAGServiceTests(TestCase):
    def test_build_device_document_includes_device_fields(self):
        user = User.objects.create_user(username="alice", password="secret")
        device = Device.objects.create(
            name="Thermostat",
            serial_number="ABC123",
            status="active",
            owner=user,
        )

        document = DeviceRAGService.build_device_document(device)

        self.assertIn("Device name: Thermostat", document)
        self.assertIn("Serial number: ABC123", document)
        self.assertIn("Status: active", document)
        self.assertIn("No sessions recorded yet", document)


class DeviceRAGQueryViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="bob", password="secret")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    @patch("devices.views.DeviceRAGService")
    def test_rag_query_returns_answer_payload(self, service_class):
        service_class.return_value.answer.return_value = {
            "answer": "Your active device is Thermostat.",
            "matches": [
                {
                    "document": "Device name: Thermostat",
                    "metadata": {"device_id": 1},
                }
            ],
        }

        response = self.client.post(
            "/devices/rag/query/",
            {"question": "Which device is active?", "limit": 2},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["answer"], "Your active device is Thermostat."
        )
        service_class.return_value.answer.assert_called_once_with(
            "Which device is active?",
            owner_id=self.user.id,
            limit=2,
        )


class DeviceRAGPlaygroundTests(TestCase):
    def test_rag_playground_page_renders(self):
        response = self.client.get("/rag/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "IoT Device RAG Playground")


class DeviceMCPToolTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="carol", password="secret")
        self.device = Device.objects.create(
            name="Sensor Hub",
            serial_number="MCP-001",
            status="offline",
            owner=self.user,
        )

    def test_list_devices_tool_filters_by_owner_and_status(self):
        other_user = User.objects.create_user(username="dave", password="secret")
        Device.objects.create(
            name="Leak Detector",
            serial_number="MCP-002",
            status="active",
            owner=other_user,
        )

        result = list_devices_tool(username="carol", status="offline")

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["owner"]["username"], "carol")
        self.assertEqual(result["devices"][0]["serial_number"], "MCP-001")

    def test_get_device_tool_returns_requested_device(self):
        result = get_device_tool(username="carol", serial_number="MCP-001")

        self.assertEqual(result["name"], "Sensor Hub")
        self.assertEqual(result["status"], "offline")
