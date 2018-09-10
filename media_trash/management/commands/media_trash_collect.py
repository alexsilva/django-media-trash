import os
import shutil
import traceback

from django.apps import apps
from django.core.files.move import file_move_safe
from django.core.management import BaseCommand

from ... import settings


class Command(BaseCommand):

    @staticmethod
    def _path_normalize(path):
        return os.path.normcase(os.path.abspath(os.path.normpath(path)))

    @classmethod
    def _is_samefile(cls, src, dst):
        if hasattr(os.path, 'samefile'):  # Macintosh, Unix.
            try:
                return os.path.samefile(src, dst)
            except OSError:
                return False
        return cls._path_normalize(src) == cls._path_normalize(dst)

    def handle(self, *args, **options):
        model = apps.get_model(*settings.MEDIA_TRASH_MODEL.split("."))

        objs = model.objects.all().trash()

        if not os.path.isdir(settings.MEDIA_TRASH_PATH):
            os.makedirs(settings.MEDIA_TRASH_PATH)

        recover_dir = settings.MEDIA_TRASH_RECOVER_DIR

        for media in objs:
            if not media.exists:
                continue

            src = media.path
            srcdir = os.path.dirname(src)

            dst = os.path.normpath(os.path.join(settings.MEDIA_TRASH_PATH, media.relpath))
            dstdir = os.path.dirname(dst)

            if os.path.isfile(src) and not os.path.isdir(dstdir):
                os.makedirs(dstdir)

            try:
                file_move_safe(src, dst, allow_overwrite=True)
            except OSError:
                # Avoid hide the error.
                print traceback.format_exc()
                continue

            media.delete()

            if not self._is_samefile(srcdir, recover_dir) and \
                    not os.listdir(srcdir):
                try:
                    shutil.rmtree(srcdir)
                except OSError:
                    pass
