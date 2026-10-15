import logging

from django.utils.translation import gettext_lazy as _
from django.core.cache import cache

from cores.models import SiteInfo

logger = logging.getLogger(__name__)

def siteinfo_processor(request):
    if request.path.startswith('/api/'):
        return {}

    cache_key = 'site_info'
    context = cache.get(cache_key)

    if context is not None:
        return context

    try:
        info = SiteInfo.objects.last()
        context = {'siteinfo': info}
        cache.set(cache_key, context, 60 * 60)  # 1 hour
        return context
    except Exception as e:
        logger.exception(f"An unexpected error occurred in function <Siteinfo Processor>: {e}")
        return {'siteinfo': None}

