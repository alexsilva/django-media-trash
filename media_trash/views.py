from django.shortcuts import render
from django.views.generic import View

from . import settings
from .base import FileListing


class MediaView(View):

    def get(self, request, *args, **kwargs):
        flisting = FileListing(settings.MEDIA_TRASH_PATH)

        context = {
            'files_walk': flisting.files_walk_filtered()
        }
        return render(request, 'media-trash/index.html', context=context)
