import os

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

MEDIA_TRASH_PATH = getattr(settings,
                           'MEDIA_TRASH_PATH',
                           os.path.abspath(os.path.join(settings.MEDIA_ROOT, '..', 'trash')))
MEDIA_TRASH_MODEL = getattr(settings, 'MEDIA_TRASH_MODEL', None)
if MEDIA_TRASH_MODEL is None:
    raise ImproperlyConfigured("trash model settings is required!")
