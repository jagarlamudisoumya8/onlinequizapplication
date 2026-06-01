from django.conf import settings


def support_settings(request):
    return {"TAWK_TO_PROPERTY_ID": settings.TAWK_TO_PROPERTY_ID}
