from django.urls import re_path

from . import views

urlpatterns = [
    re_path(
        r"^calendar/(?P<gid>\d+)/today/$",
        views.today_view,
        name="swingtime-today",
    ),
    re_path(
        r"^calendar/(?P<gid>\d+)/(?P<year>\d{4})/$",
        views.year_view,
        name="swingtime-yearly-view",
    ),
    re_path(
        r"^calendar/(?P<gid>\d+)/(?P<year>\d{4})/(?P<month>0?[1-9]|1[012])/$",
        views.month_view,
        name="swingtime-monthly-view",
    ),
    re_path(
        r"^calendar/(\d+)/(\d{4})/(0?[1-9]|1[012])/([0-3]?\d)/$",
        views.day_view,
        name="swingtime-daily-view",
    ),
    re_path(r"^events/(?P<gid>\d+)/$", views.event_listing, name="swingtime-events"),
    re_path(r"^events/(?P<gid>\d+)/add/$", views.add_event, name="swingtime-add-event"),
    re_path(r"^events/(\d+)/detail/(\d+)/$", views.event_view, name="swingtime-event"),
    re_path(
        r"^events/(\d+)/detail/(\d+)/(\d+)/$",
        views.occurrence_view,
        name="swingtime-occurrence",
    ),
]
