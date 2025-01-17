"""
Common features and functions for jivetime
"""
import calendar
from copy import copy
from datetime import date, datetime, time, timedelta, tzinfo

import pytz

from .conf import jivetime_settings
from .models import Occurrence


def month_boundaries(dt=None):
    """
    Return a 2-tuple containing the datetime instances for the first and last
    dates of the current month or using ``dt`` as a reference.

    """
    dt = dt or date.today()
    wkday, ndays = calendar.monthrange(dt.year, dt.month)
    start = datetime(dt.year, dt.month, 1)
    return (start, start + timedelta(ndays - 1))


def create_timeslot_table(
    dt: datetime,
    start_time: time = jivetime_settings.TIMESLOT_START_TIME,
    end_time_delta: timedelta = jivetime_settings.TIMESLOT_END_TIME_DURATION,
    time_delta: timedelta = jivetime_settings.TIMESLOT_INTERVAL,
    min_columns=jivetime_settings.TIMESLOT_MIN_COLUMNS,
) -> list:
    """
    Create a grid-like object representing a sequence of times (rows) and
    columns where cells are either empty or reference a wrapper object for
    event occasions that overlap a specific time slot.

    Currently, there is an assumption that if an occurrence has a ``start_time``
    that falls with the temporal scope of the grid, then that ``start_time`` will
    also match an interval in the sequence of the computed row entries.

    * ``dt`` - a ``datetime.datetime`` instance
    * ``start_time`` - a ``datetime.time`` instance
    * ``end_time_delta`` - a ``datetime.timedelta`` instance
    * ``time_delta`` - a ``datetime.timedelta`` instance
    * ``min_column`` - the minimum number of columns to show in the table
    * ``proxy_class`` - a wrapper class for accessing an ``Occurrence`` object.
      This class should also expose ``event_type`` and ``event_type`` attrs, and
      handle the custom output via its __unicode__ method.

    """
    dtstart = datetime.combine(dt.date(), start_time, tzinfo=pytz.UTC)
    dtend = dtstart + end_time_delta

    items = Occurrence.objects.daily_occurrences(dt).select_related("event")

    # build a mapping of timeslot "buckets"
    timeslots: dict = {}
    n = dtstart
    while n <= dtend:
        timeslots[n] = {}
        n += time_delta

    # fill the timeslot buckets with occurrence proxies
    for item in sorted(items):
        if item.end_time <= dtstart:
            # this item began before the start of our schedule constraints
            continue

        if item.start_time > dtstart:
            rowkey = current = item.start_time
        else:
            rowkey = current = dtstart

        timeslot = timeslots.get(rowkey)
        if timeslot is None:
            # TODO fix atypical interval boundary spans
            # This is rather draconian, we should probably try to find a better
            # way to indicate that this item actually occurred between 2 intervals
            # and to account for the fact that this item may be spanning cells
            # but on weird intervals
            continue

        colkey = 0
        while 1:
            # keep searching for an open column to place this occurrence
            if colkey not in timeslot:
                timeslot[colkey] = item

                while current < item.end_time:
                    rowkey = current
                    row = timeslots.get(rowkey)
                    if row is None:
                        break

                    # we might want to put a sanity check in here to ensure that
                    # we aren't trampling some other entry, but by virtue of
                    # sorting all occurrence that shouldn't happen
                    row[colkey] = item
                    current += time_delta
                break

            colkey += 1

    # determine the number of timeslot columns we should show
    column_lens = [len(x) for x in timeslots.values()]
    column_count = max((min_columns, max(column_lens) if column_lens else 0))
    empty_columns = [""] * column_count

    # create the chronological grid layout
    table = []

    for rowkey in sorted(timeslots.keys()):
        cols = empty_columns[:]
        for colkey in timeslots[rowkey]:
            cols[colkey] = timeslots[rowkey][colkey]

        table.append((rowkey, cols))
    return table
