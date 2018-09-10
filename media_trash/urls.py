from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from . import views, settings

urlpatterns = [
    url("^$", login_required(views.MediaView.as_view(),
                             login_url=settings.MEDIA_TRASH_LOGIN_URL),
        name='media-trash')
]
