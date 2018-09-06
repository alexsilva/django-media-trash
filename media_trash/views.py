from django.shortcuts import render
from django.views.generic import View


class MediaView(View):

    def get(self, request, *args, **kwargs):
        context = {}
        return render(request, 'media-trash/index.html', context=context)
