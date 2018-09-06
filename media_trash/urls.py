from django.conf.urls import url
from . import views

urlpatterns = [
    url("^$", views.MediaView.as_view(), name='media-trash')
]
