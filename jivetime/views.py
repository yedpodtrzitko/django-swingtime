import calendar
import itertools
import logging
from datetime import date, datetime, timedelta
from enum import Enum
from typing import List, Tuple

from dateutil import parser
from django import http
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

from . import forms, utils
from .conf import jivetime_settings
from .forms import WEEKDAY_SHORT
from .models import Event, EventGroup, Occurrence

if jivetime_settings.CALENDAR_FIRST_WEEKDAY is not None:
    calendar.setfirstweekday(jivetime_settings.CALENDAR_FIRST_WEEKDAY)


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
        initial={"dtstart": datetime.now(tz=group.timezone)}
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
                return http.HttpResponseRedirect(request.path)
        elif "_delete" in request.POST:
            event.delete()
            return http.HttpResponseRedirect(
                reverse("swingtime-today", args=[group.id])
            )
        else:
            return http.HttpResponseBadRequest("Bad Request")

    occurrences = event.occurrence_set.all()
    nav_date = datetime.now(tz=group.timezone)
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
    assert group.id == int(gid)

    if request.method == "POST":
        if "_delete" in request.POST:
            st = occurrence.start_time
            occurrence.delete()
            return http.HttpResponseRedirect(
                reverse(
                    "swingtime-daily-view", args=[group.id, st.year, st.month, st.day]
                )
            )

        form = form_class(request.POST, instance=occurrence)
        if form.is_valid():
            form.save()
            st = occurrence.start_time
            return http.HttpResponseRedirect(
                reverse(
                    "swingtime-daily-view", args=[group.id, st.year, st.month, st.day]
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


def add_event(
    request,
    gid: int,
    template="jivetime/add_event.html",
):
    """
    Add a new ``Event`` instance and 1 or more associated ``Occurrence``s.

    Context parameters:

    ``dtstart``
        a datetime.datetime object representing the GET request value if present,
        otherwise None

    ``event_form``
        a form object for updating the event

    ``recurrence_form``
        a form object for adding occurrences

    """
    group = get_object_or_404(EventGroup, pk=int(gid))
    event_form = EventFormClass(initial=dict(group=group.id))
    dtstart = datetime.now(tz=group.timezone)

    if request.method == "POST":
        event_form = EventFormClass(request.POST)
        recurrence_form = ReccurrenceFormClass(request.POST)
        if event_form.is_valid() and recurrence_form.is_valid():
            event = event_form.save(commit=False)
            event.group = group
            event.save()
            recurrence_form.save(event)
            return http.HttpResponseRedirect(event.get_absolute_url())

    else:
        if "dtstart" in request.GET:
            try:
                dtstart = parser.parse(request.GET["dtstart"])
            except (TypeError, ValueError) as e:
                # TODO: A badly formatted date is passed to add_event
                logging.warning(e)
        recurrence_form = ReccurrenceFormClass(initial={"dtstart": dtstart})

    return render(
        request,
        template,
        {
            "group": group,
            "dtstart": dtstart,
            "event_form": event_form,
            "recurrence_form": recurrence_form,
        },
    )


def _datetime_view(request, template: str, group: EventGroup, dt: datetime, **params):
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
            "timeslots": utils.create_timeslot_table(group.timezone, dt, **params),
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
    **params
):
    """
    See documentation for function``_datetime_view``.

    """
    group = get_object_or_404(EventGroup, pk=int(gid))
    if request.method == "POST" and "_goto" in request.POST:
        dt = datetime.strptime(request.POST.get("date"), "%Y-%m-%d")
        return redirect(
            reverse("swingtime-daily-view", args=[group.id, dt.year, dt.month, dt.day])
        )

    dt = datetime(int(year), int(month), int(day), tzinfo=group.timezone)
    return _datetime_view(request, template, group, dt, **params)


def today_view(request, gid: int, template="jivetime/daily_view.html", **params):
    """
    See documentation for function``_datetime_view``.

    """
    group = EventGroup.objects.get(pk=gid)
    dt = datetime.now(tz=group.timezone)
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
    group = get_object_or_404(EventGroup, pk=int(gid))
    if request.method == "POST" and request.POST.get("date"):
        sent = parser.parse(request.POST["date"])
        year = sent.year
        return redirect(reverse("swingtime-yearly-view", args=[group.id, year]))

    year = int(year)
    occurrences = Occurrence.objects.filter(
        models.Q(start_time__year=year) | models.Q(end_time__year=year)
    )

    def group_key(o):
        return datetime(
            year,
            o.start_time.month if o.start_time.year == year else o.end_time.month,
            1,
        )

    return render(
        request,
        template,
        {
            "today": date(year, 1, 1),
            "group": group,
            "year": year,
            "by_month": [
                (dt, list(o)) for dt, o in itertools.groupby(occurrences, group_key)
            ],
            "next_year": year + 1,
            "last_year": year - 1,
            "scope_menu": get_scope_menu(gid, datetime(year, 1, 1)),
            "scope_id": ScopeEnum.YEAR,
        },
    )


class ScopeEnum(str, Enum):
    YEAR = "year"
    MONTH = "month"
    DAY = "day"


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
            _("Montly View"),
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


def month_view(
    request,
    gid: int,
    year: int,
    month: int,
    template="jivetime/monthly_view.html",
    queryset=None,
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
    group = get_object_or_404(EventGroup, pk=int(gid))
    year, month = int(year), int(month)
    cal_data = calendar.monthcalendar(year, month)
    dtstart = datetime(year, month, 1)
    last_day = max(cal_data[-1])

    # TODO Whether to include those occurrences that started in the previous
    # month but end in this month?
    queryset = (
        queryset._clone()
        if queryset is not None
        else Occurrence.objects.select_related()
    )
    occurrences = queryset.filter(start_time__year=year, start_time__month=month)

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
