import os
import urllib

from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import View

from . import settings
from .base import FileListing, FileObject


class MediaView(View):

    def __init__(self, *args, **kwargs):
        super(MediaView, self).__init__(*args, **kwargs)

        self.file_listing = FileListing(settings.MEDIA_TRASH_PATH)

    def get(self, request, *args, **kwargs):
        context = {
            'files_walk': self.file_listing.files_walk_filtered()
        }
        return render(request, 'media-trash/index.html', context=context)

    def post(self, request, *args, **kwargs):
        post = request.POST

        relpath = urllib.unquote_plus(post.get('relpath'))

        fileobject = FileObject(relpath, storage=self.file_listing.storage)

        if fileobject.exists:
            filepath = os.path.join(settings.MEDIA_TRASH_RECOVER_DIR, fileobject.path_relative_directory)
            fileobject.move(filepath)

        return HttpResponseRedirect(request.path)
