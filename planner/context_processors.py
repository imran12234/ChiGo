from django.conf import settings


def google_maps(request):
    """Expose only the explicitly configured browser key, never the Places key."""
    return {
        'google_maps_browser_key': settings.GOOGLE_MAPS_BROWSER_KEY,
        'google_maps_map_id': settings.GOOGLE_MAPS_MAP_ID,
    }
