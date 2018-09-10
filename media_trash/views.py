import os
import urllib

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.module_loading import import_string
from django.views.generic import View

from . import settings
from .base import FileListing, FileObject


class MediaView(View):

    def __init__(self, *args, **kwargs):
        super(MediaView, self).__init__(*args, **kwargs)

        self.file_listing = FileListing(settings.MEDIA_TRASH_PATH)

    def get(self, request, *args, **kwargs):
        context = {
            'files_walk': self.file_listing.files_walk_filtered(),
        }
        if isinstance(settings.MEDIA_TRASH_GET_BACK_URL, basestring):
            context['back_url'] = import_string(settings.MEDIA_TRASH_GET_BACK_URL)(request, **kwargs)

        if settings.MEDIA_TRASH_BUTTON_BACK_TITLE:
            context['return_button_title'] = settings.MEDIA_TRASH_BUTTON_BACK_TITLE

        return render(request, 'media-trash/index.html', context=context)

    def post(self, request, *args, **kwargs):
        post = request.POST

        relpath = urllib.unquote_plus(post.get('relpath'))

        fileobject = FileObject(relpath, storage=self.file_listing.storage)

        if fileobject.exists:
            filepath = os.path.join(settings.MEDIA_TRASH_RECOVER_DIR, fileobject.path_relative_directory)
            try:
                fileobject.move(filepath)
                messages.success(request, render_to_string('media-trash/restore-success.html', context=dict(
                    filepath=relpath
                )))
            except Exception as exc:
                messages.error(request, render_to_string('media-trash/restore-error.html', context=dict(
                    filepath=relpath,
                    exc=exc
                )))
        return HttpResponseRedirect(request.path)
