import os

from django.contrib import admin
from django.urls import include, re_path
from django.views.generic import RedirectView, TemplateView
from django.views.static import serve

doc_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs/")


def docs(request):
    from django import http

    return http.HttpResponsePermanentRedirect(os.path.join(request.path, "index.html"))


jivetime_patterns = [
    re_path(r"^$", TemplateView.as_view(template_name="intro.html"), name="demo-home"),
    re_path(r"^karate/", include("karate.urls")),
    re_path(r"^admin/", admin.site.urls),
    re_path(r"^docs/$", docs, name="swingtime-docs"),
    re_path(
        r"^docs/(?P<path>.*)$", serve, dict(document_root=doc_root, show_indexes=False)
    ),
]

urlpatterns = [
    re_path(r"^$", RedirectView.as_view(url="/swingtime/")),
    re_path(r"^jivetime/", include(jivetime_patterns)),
]
