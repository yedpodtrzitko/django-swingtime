from django.conf.urls import include
from django.urls import path, re_path
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    path(r"^$", TemplateView.as_view(template_name="karate.html"), name="karate-home"),
    path(r"^jivetime/", include("jivetime.urls")),
    re_path(r"^jivetime/events/type/([^/]+)/$", views.event_type, name="karate-event"),
]
