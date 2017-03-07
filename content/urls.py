from django.conf.urls import url

from content.views import LandingView, email_opened


urlpatterns = [
    url(r'^$', LandingView.as_view(), name='landing'),
    url(r'^opened/$', email_opened, name='on_email_opened'),
]
