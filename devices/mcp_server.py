from __future__ import annotations

import asyncio
import os
from functools import partial
from typing import Any

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "iot_project.settings")


def setup_django() -> None:
    import django
    from django.apps import apps

    if not apps.ready:
        django.setup()

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover - exercised only when MCP is installed.
    FastMCP = None


def _resolve_owner(*, owner_id: int | None = None, username: str | None = None):
    setup_django()
    from django.contrib.auth.models import User
    from django.core.exceptions import ObjectDoesNotExist

    if owner_id is None and not username:
        raise ValueError("Provide either owner_id or username.")

    if owner_id is not None:
        try:
            return User.objects.get(pk=owner_id)
        except ObjectDoesNotExist as exc:
            raise ValueError(f"No user found for owner_id={owner_id}.") from exc

    try:
        return User.objects.get(username=username)
    except ObjectDoesNotExist as exc:
        raise ValueError(f"No user found for username='{username}'.") from exc


def _serialize_device(device) -> dict[str, Any]:
    setup_django()

    sessions = [
        {
            "start_time": session.start_time.isoformat(),
            "energy_consumed": session.energy_consumed,
        }
        for session in device.sessions.all().order_by("-start_time")[:5]
    ]

    return {
        "id": device.pk,
        "name": device.name,
        "serial_number": device.serial_number,
        "status": device.status,
        "owner_id": device.owner_id,
        "created_at": device.created_at.isoformat(),
        "recent_sessions": sessions,
    }


def list_devices_tool(
    *,
    owner_id: int | None = None,
    username: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    setup_django()
    from .models import Device

    owner = _resolve_owner(owner_id=owner_id, username=username)
    queryset = Device.objects.filter(owner=owner).prefetch_related("sessions")
    if status:
        queryset = queryset.filter(status=status)

    devices = [_serialize_device(device) for device in queryset.order_by("id")]
    return {
        "owner": {
            "id": owner.id,
            "username": owner.username,
        },
        "count": len(devices),
        "devices": devices,
    }


def get_device_tool(
    *,
    device_id: int | None = None,
    serial_number: str | None = None,
    owner_id: int | None = None,
    username: str | None = None,
) -> dict[str, Any]:
    setup_django()
    from .models import Device

    if device_id is None and not serial_number:
        raise ValueError("Provide either device_id or serial_number.")

    owner = _resolve_owner(owner_id=owner_id, username=username)
    queryset = Device.objects.filter(owner=owner).prefetch_related("sessions")

    if device_id is not None:
        queryset = queryset.filter(pk=device_id)
    else:
        queryset = queryset.filter(serial_number=serial_number)

    device = queryset.first()
    if device is None:
        raise ValueError("No matching device found for the provided owner.")

    return _serialize_device(device)


def ask_devices_rag_tool(
    question: str,
    *,
    owner_id: int | None = None,
    username: str | None = None,
    limit: int = 3,
) -> dict[str, Any]:
    setup_django()
    from .rag import DeviceRAGService

    owner = _resolve_owner(owner_id=owner_id, username=username)
    service = DeviceRAGService()
    return service.answer(question, owner_id=owner.id, limit=limit)


def rebuild_device_index_tool(
    *,
    owner_id: int | None = None,
    username: str | None = None,
) -> dict[str, Any]:
    setup_django()
    from .models import Device
    from .rag import DeviceRAGService

    owner = _resolve_owner(owner_id=owner_id, username=username)
    queryset = (
        Device.objects.filter(owner=owner)
        .select_related("owner")
        .prefetch_related("sessions")
    )
    service = DeviceRAGService()
    count = service.upsert_devices(queryset)
    return {
        "owner": {
            "id": owner.id,
            "username": owner.username,
        },
        "indexed_count": count,
    }


def rebuild_all_device_indexes_tool() -> dict[str, Any]:
    setup_django()
    from django.core.management import call_command

    call_command("rebuild_device_rag")
    return {
        "status": "ok",
        "message": "Triggered Django rebuild_device_rag for all devices.",
    }


async def _run_in_thread(func, *args, **kwargs):
    """Run a synchronous function in a thread pool to avoid blocking the async event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(func, *args, **kwargs))


def create_mcp_server():
    setup_django()

    if FastMCP is None:
        raise RuntimeError(
            "The MCP SDK is not installed. Add the 'mcp' package from requirements.txt first."
        )

    server = FastMCP("iot-project")

    @server.tool()
    async def list_devices(
        owner_id: int | None = None,
        username: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """List devices for a single owner, optionally filtered by status."""
        return await _run_in_thread(
            list_devices_tool, owner_id=owner_id, username=username, status=status
        )

    @server.tool()
    async def get_device(
        device_id: int | None = None,
        serial_number: str | None = None,
        owner_id: int | None = None,
        username: str | None = None,
    ) -> dict[str, Any]:
        """Fetch one device for a single owner by id or serial number."""
        return await _run_in_thread(
            get_device_tool,
            device_id=device_id,
            serial_number=serial_number,
            owner_id=owner_id,
            username=username,
        )

    @server.tool()
    async def ask_devices_rag(
        question: str,
        owner_id: int | None = None,
        username: str | None = None,
        limit: int = 3,
    ) -> dict[str, Any]:
        """Answer a device question using the existing RAG pipeline."""
        return await _run_in_thread(
            ask_devices_rag_tool,
            question,
            owner_id=owner_id,
            username=username,
            limit=limit,
        )

    @server.tool()
    async def rebuild_device_index(
        owner_id: int | None = None,
        username: str | None = None,
    ) -> dict[str, Any]:
        """Reindex devices for one owner into Chroma."""
        return await _run_in_thread(
            rebuild_device_index_tool, owner_id=owner_id, username=username
        )

    @server.tool()
    async def rebuild_all_device_indexes() -> dict[str, Any]:
        """Reindex every device in the project into Chroma."""
        return await _run_in_thread(rebuild_all_device_indexes_tool)

    return server


def main() -> None:
    server = create_mcp_server()
    server.run()


if __name__ == "__main__":
    main()