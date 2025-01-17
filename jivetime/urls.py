from django.urls import re_path

from . import views

app_name = "jivetime"
urlpatterns = [
    re_path(
        r"^calendar/(?P<gid>\d+)/today/$",
        views.today_view,
        name="calendar-today",
    ),
    re_path(
        r"^calendar/(?P<gid>\d+)/(?P<year>\d{4})/$",
        views.year_view,
        name="calendar-year",
    ),
    re_path(
        r"^calendar/(?P<gid>\d+)/(?P<year>\d{4})/(?P<month>0?[1-9]|1[012])/$",
        views.month_view,
        name="calendar-month",
    ),
    re_path(
        r"^calendar/(?P<gid>\d+)/month-current/$",
        views.month_current,
        name="calendar-month-current",
    ),
    re_path(
        r"^calendar/(\d+)/(\d{4})/(0?[1-9]|1[012])/([0-3]?\d)/$",
        views.day_view,
        name="calendar-day",
    ),
    re_path(r"^events/(?P<gid>\d+)/$", views.event_listing, name="event-list"),
    re_path(
        r"^events/(?P<gid>\d+)/add/$", views.EventAddView.as_view(), name="event-add"
    ),
    re_path(r"^events/(\d+)/detail/(\d+)/$", views.event_view, name="event-detail"),
    re_path(
        r"^events/(\d+)/detail/(\d+)/(\d+)/$",
        views.occurrence_view,
        name="event-occurrence",
    ),
]
