from ipaddress import ip_address

from django.conf import settings
from django.http import HttpResponse, JsonResponse


def client_ip(request):
    """Trust forwarding headers only behind the documented Vercel ingress."""
    raw = request.META.get("REMOTE_ADDR", "")
    if settings.IS_VERCEL:
        raw = request.META.get("HTTP_X_VERCEL_FORWARDED_FOR", raw)
    try:
        return str(ip_address(raw.strip()))
    except ValueError:
        return None


def lockout_response(request, response=None, credentials=None, *args, **kwargs):
    message = "Too many failed sign-in attempts. Try again in 15 minutes."
    if request.path.startswith("/api/"):
        result = JsonResponse({"detail": message}, status=429)
    else:
        result = HttpResponse(message, status=429, content_type="text/plain; charset=utf-8")
    result["Retry-After"] = "900"
    result["Cache-Control"] = "no-store"
    return result
