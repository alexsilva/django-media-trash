import os
import shutil

from django.apps import apps
from django.core.management import BaseCommand

from ... import settings


class Command(BaseCommand):

    def handle(self, *args, **options):
        model = apps.get_model(*settings.MEDIA_TRASH_MODEL.split("."))

        objs = model.objects.all().trash()

        if not os.path.isdir(settings.MEDIA_TRASH_PATH):
            os.makedirs(settings.MEDIA_TRASH_PATH)

        for media in objs:
            if not media.exists:
                continue

            src = media.path
            srcdir = os.path.dirname(src)

            dst = os.path.normpath(os.path.join(settings.MEDIA_TRASH_PATH, media.relpath))
            dstdir = os.path.dirname(dst)

            if os.path.isfile(src) and not os.path.isdir(dstdir):
                os.makedirs(dstdir)

            shutil.copy2(src, dst)

            if os.path.exists(dst):
                os.remove(src)

            if len(os.listdir(dstdir)) == 0:
                os.remove(srcdir)

        objs.delete()
