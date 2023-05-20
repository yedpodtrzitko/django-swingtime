import calendar
import itertools
import logging
from datetime import date, datetime, timedelta
from enum import Enum
from typing import List, Tuple

import pytz
from dateutil import parser
from django import http
from django.apps import apps
from django.contrib import messages
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView

from . import forms, utils
from .conf import jivetime_settings
from .forms import WEEKDAY_SHORT
from .models import Event, Occurrence

if jivetime_settings.CALENDAR_FIRST_WEEKDAY is not None:
    calendar.setfirstweekday(jivetime_settings.CALENDAR_FIRST_WEEKDAY)

logger = logging.getLogger(__name__)


class ScopeEnum(str, Enum):
    YEAR = "year"
    MONTH = "month"
    DAY = "day"


def load_config_form(form_class):
    if isinstance(form_class, str):
        return import_string(form_class)
    elif callable(form_class):
        return form_class()
    return form_class


EventFormClass = load_config_form(jivetime_settings.FORM_EVENT)
ReccurrenceFormClass = load_config_form(jivetime_settings.FORM_RECURRENCE)


def event_listing(
    request, template="jivetime/event_list.html", events=None, **extra_context
):
    """
    View all ``events``.

    If ``events`` is a queryset, clone it. If ``None`` default to all ``Event``s.

    Context parameters:

    ``events``
        an iterable of ``Event`` objects

    ... plus all values passed in via **extra_context
    """
    events = events or Event.objects.all()
    extra_context["events"] = events
    return render(request, template, extra_context)


def event_view(
    request,
    gid: int,
    pk: int,
    template="jivetime/event_detail.html",
):
    """
    View an ``Event`` instance and optionally update either the event or its
    occurrences.

    Context parameters:

    ``event``
        the event keyed by ``pk``

    """

    event = get_object_or_404(Event, pk=int(pk), group_id=int(gid))
    group = event.group
    recurrence_form = ReccurrenceFormClass(
        initial={"dtstart": datetime.now()},
    )

    event_form = EventFormClass(instance=event)
    if request.method == "POST":
        if "_update" in request.POST:
            event_form = EventFormClass(request.POST, instance=event)
            if event_form.is_valid():
                event_form.save(event)
                return http.HttpResponseRedirect(request.path)
        elif "_add" in request.POST:
            recurrence_form = ReccurrenceFormClass(request.POST)
            if recurrence_form.is_valid():
                recurrence_form.save(event)

                messages.add_message(
                    request, messages.SUCCESS, "Occurrence added successfully."
                )
                return http.HttpResponseRedirect(request.path)
        elif "_delete" in request.POST:
            event.delete()
            return http.HttpResponseRedirect(
                reverse("jivetime:calendar-today", args=[group.id])
            )
        else:
            return http.HttpResponseBadRequest("Bad Request")

    occurrences = event.occurrence_set.all()
    nav_date = datetime.now()
    if occurrences:
        nav_date = occurrences[0].start_time.date()

    data = {
        "today": date.today(),
        "group": event.group,
        "event": event,
        "occurrences": occurrences,
        "event_form": event_form,
        "recurrence_form": recurrence_form,
        "scope_menu": get_scope_menu(group.id, nav_date),
    }
    return render(request, template, data)


def occurrence_view(
    request,
    gid: int,
    event_pk: int,
    pk: int,
    template="jivetime/occurrence_detail.html",
    form_class=forms.SingleOccurrenceForm,
):
    """
    View a specific occurrence and optionally handle any updates.

    Context parameters:

    ``occurrence``
        the occurrence object keyed by ``pk``

    ``form``
        a form object for updating the occurrence
    """
    occurrence = get_object_or_404(Occurrence, pk=pk, event_id=event_pk)
    group = occurrence.event.group

    if request.method == "POST":
        if "_delete" in request.POST:
            st = occurrence.start_time
            occurrence.delete()
            return http.HttpResponseRedirect(
                reverse(
                    "jivetime:calendar-day", args=[group.id, st.year, st.month, st.day]
                )
            )

        form = form_class(request.POST, instance=occurrence)
        if form.is_valid():
            form.save()
            st = occurrence.start_time
            return http.HttpResponseRedirect(
                reverse(
                    "jivetime:calendar-day", args=[group.id, st.year, st.month, st.day]
                )
            )
    else:
        form = form_class(instance=occurrence)

    return render(
        request,
        template,
        {
            "scope_menu": get_scope_menu(group.id, occurrence.start_time),
            "group": group,
            "occurrence": occurrence,
            "form": form,
        },
    )


class EventAddView(CreateView):
    model = Event
    template_name = "jivetime/add_event.html"

    def get_form_class(self):
        return EventFormClass

    def get_form_class_recc(self):
        return ReccurrenceFormClass

    def dispatch(self, request, *args, **kwargs):
        self.group = get_event_group(self.kwargs["gid"])
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        event_form = self.get_form()
        recurrence_form = self.get_form_class_recc()(request.POST)

        if event_form.is_valid() and recurrence_form.is_valid():
            event = event_form.save(commit=False)
            event.group = self.group
            event.save()
            self.object = event
            recurrence_form.save(event)
            return http.HttpResponseRedirect(self.get_success_url())

        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("jivetime:event-detail", args=[self.group.id, self.object.pk])

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)

        dtstart = datetime.now(tz=self.group.timezone).replace(tzinfo=pytz.UTC)
        if "dtstart" in self.request.GET:
            try:
                dtstart = parser.parse(self.request.GET["dtstart"])
            except parser.ParserError:
                logger.error("failed to parse dstart")

        start_time = int(dtstart.time().hour * 3600 + dtstart.minute * 60)
        data["group"] = self.group
        data["recurrence_form"] = self.get_form_class_recc()(
            initial={
                "start_time_delta": start_time,
                "end_time_delta": start_time + 3600,
                "day": dtstart.date(),
            },
        )
        return data


def _datetime_view(request, template: str, group, dt: datetime, **params):
    """
    Build a time slot grid representation for the given datetime ``dt``. See
    utils.create_timeslot_table documentation for items and params.

    Context parameters:

    ``day``
        the specified datetime value (dt)

    ``next_day``
        day + 1 day

    ``prev_day``
        day - 1 day

    ``timeslots``
        time slot grid of (time, cells) rows

    """
    return render(
        request,
        template,
        {
            "group": group,
            "day": dt,
            "next_day": dt + timedelta(days=+1),
            "prev_day": dt + timedelta(days=-1),
            "timeslots": utils.create_timeslot_table(dt, **params),
            "scope_id": ScopeEnum.DAY,
            "scope_menu": get_scope_menu(group.id, dt),
        },
    )


def day_view(
    request,
    gid: int,
    year: int,
    month: int,
    day: int,
    template="jivetime/daily_view.html",
    **params,
):
    """
    See documentation for function``_datetime_view``.

    """
    group = get_event_group(gid)
    dt = datetime(int(year), int(month), int(day))  # , tzinfo=group.timezone)
    return _datetime_view(request, template, group, dt, **params)


def today_view(request, gid: int, template="jivetime/daily_view.html", **params):
    """
    See documentation for function``_datetime_view``.

    """
    group = get_event_group(gid)
    dt = datetime.now(tz=group.timezone).replace(tzinfo=None)
    return _datetime_view(request, template, group, dt, **params)


def year_view(request, gid: int, year: int, template="jivetime/yearly_view.html"):
    """

    Context parameters:

    ``year``
        an integer value for the year in questin

    ``next_year``
        year + 1

    ``last_year``
        year - 1

    ``by_month``
        a sorted list of (month, occurrences) tuples where month is a
        datetime.datetime object for the first day of a month and occurrences
        is a (potentially empty) list of values for that month. Only months
        which have at least 1 occurrence is represented in the list

    """
    group = get_event_group(gid)
    if request.method == "POST" and "_goto" in request.POST:
        dt = datetime.strptime(request.POST.get("date"), "%Y-%m-%d")

        scope = request.POST.get("_scope")
        if scope == "calendar-day":
            args = [group.id, dt.year, dt.month, dt.day]
        elif scope == "calendar-year":
            args = [
                group.id,
                dt.year,
            ]
        else:
            scope = "calendar-month"
            args = [
                group.id,
                dt.year,
                dt.month,
            ]

        return redirect(reverse(f"jivetime:{scope}", args=args))

    year = int(year)
    occurrences = Occurrence.objects.filter(
        models.Q(start_time__year=year) | models.Q(end_time__year=year),
        event__group_id=group.id,
    )

    by_month = {date(year, idx, 1): [] for idx in range(1, 13)}
    for o in occurrences:
        by_month[date(o.start_time.year, o.start_time.month, 1)].append(o)

    return render(
        request,
        template,
        {
            "today": date(year, 1, 1),
            "group": group,
            "year": year,
            "by_month": by_month,
            "next_year": year + 1,
            "last_year": year - 1,
            "scope_menu": get_scope_menu(gid, datetime(year, 1, 1)),
            "scope_id": ScopeEnum.YEAR,
        },
    )


def get_scope_menu(gid: int, dt: datetime) -> List[Tuple[str, str, str]]:
    return [
        (
            ScopeEnum.YEAR,
            reverse("jivetime:calendar-year", args=[gid, dt.year]),
            _("Yearly View"),
        ),
        (
            ScopeEnum.MONTH,
            reverse("jivetime:calendar-month", args=[gid, dt.year, dt.month]),
            _("Monthly View"),
        ),
        (
            ScopeEnum.DAY,
            reverse("jivetime:calendar-day", args=[gid, dt.year, dt.month, dt.day]),
            _("Daily View"),
        ),
    ]


def month_current(request, gid: int):
    # TODO - timezone
    today = datetime.today()
    return redirect(
        reverse("jivetime:calendar-month", args=[gid, today.year, today.month])
    )


def get_event_group(group_id, key_type=int):
    model_path = jivetime_settings.EVENT_GROUP_MODEL
    ModelClass = apps.get_model(*model_path.split("."))
    return get_object_or_404(ModelClass, pk=key_type(group_id))


def month_view(
    request,
    gid: int,
    year: int,
    month: int,
    template="jivetime/monthly_view.html",
):
    """
    Render a traditional calendar grid view with temporal navigation variables.

    Context parameters:

    ``today``
        the current datetime.datetime value

    ``calendar``
        a list of rows containing (day, items) cells, where day is the day of
        the month integer and items is a (potentially empty) list of occurrence
        for the day

    ``this_month``
        a datetime.datetime representing the first day of the month

    ``next_month``
        this_month + 1 month

    ``last_month``
        this_month - 1 month

    """

    group = get_event_group(gid)
    year, month = int(year), int(month)
    cal_data = calendar.monthcalendar(year, month)
    dtstart = datetime(year, month, 1)
    last_day = max(cal_data[-1])

    occurrences = Occurrence.objects.filter(
        start_time__year=year,
        start_time__month=month,
        event__group_id=group.id,
    ).select_related()

    def start_day(o):
        return o.start_time.day

    by_day = dict(
        [(dt, list(o)) for dt, o in itertools.groupby(occurrences, start_day)]
    )
    data = {
        "today": datetime.now(),
        "group": group,
        "calendar_data": [[(d, by_day.get(d, [])) for d in row] for row in cal_data],
        "this_month": dtstart,
        "next_month": dtstart + timedelta(days=+last_day),
        "last_month": dtstart + timedelta(days=-1),
        "week_days": [x for (_, x) in WEEKDAY_SHORT],
        "scope_menu": get_scope_menu(gid, dtstart),
        "scope_id": ScopeEnum.MONTH,
    }

    return render(request, template, data)
