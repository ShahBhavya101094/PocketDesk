from django.conf import settings


def auth_options(request):
    return {"public_signup_enabled": settings.PUBLIC_SIGNUP_ENABLED}
