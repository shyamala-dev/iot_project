from django.http import JsonResponse


class BlockMaintenanceDevicesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Example: block write methods for unauthenticated users
        if request.path.startswith("/api/devices/") and request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            if not request.user.is_authenticated:
                return JsonResponse({"detail": "Authentication required"}, status=401)

        return self.get_response(request)