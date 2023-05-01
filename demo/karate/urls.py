from django.conf.urls import include
from django.urls import path, re_path
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    path(r"^$", TemplateView.as_view(template_name="karate.html"), name="karate-home"),
    path(r"^swingtime/", include("swingtime.urls")),
    re_path(r"^swingtime/events/type/([^/]+)/$", views.event_type, name="karate-event"),
]
