from datetime import datetime

import pytest
from django.contrib.auth.models import User

from swingtime.models import Event, EventGroup, EventType, Occurrence

GROUP_DEFAULT_ID = 1


@pytest.fixture
def group_default():
    def create_group(**kwargs):
        defaults = {"name": "testing group", **kwargs}
        g, _ = EventGroup.objects.get_or_create(
            id=GROUP_DEFAULT_ID,
            defaults=defaults,
        )
        return g

    return create_group


@pytest.fixture
def work_type():
    # 2
    return EventType.objects.create(abbr="work", label="Work")


@pytest.fixture
def play_type():
    # 1
    return EventType.objects.create(abbr="play", label="Play")


@pytest.fixture
def occurence(work_type, group_default):
    e = Event.objects.create(event_type=work_type, title="event", group=group_default())
    return Occurrence.objects.create(
        event=e,
        start_time=datetime(2018, 3, 18, 16, 00),
        end_time=datetime(2018, 3, 18, 16, 45),
    )


@pytest.fixture
def events(play_type, work_type, group_default):
    owner = User.objects.create_user("test_user")
    g = group_default(owner=owner)

    e = Event.objects.create(event_type=play_type, title="bravo", group=g)
    Occurrence.objects.create(
        event=e,
        start_time=datetime(2008, 12, 11, 16, 00),
        end_time=datetime(2008, 12, 11, 16, 45),
    )

    e = Event.objects.create(event_type=work_type, title="echo", group=g)
    Occurrence.objects.create(
        event=e,
        start_time=datetime(2008, 12, 11, 17, 15),
        end_time=datetime(2008, 12, 11, 18, 00),
    )

    e = Event.objects.create(event_type=play_type, title="charlie", group=g)
    Occurrence.objects.create(
        event=e,
        start_time=datetime(2008, 12, 11, 16, 15),
        end_time=datetime(2008, 12, 11, 17, 00),
    )

    e = Event.objects.create(event_type=work_type, title="foxtrot", group=g)
    Occurrence.objects.create(
        event=e,
        start_time=datetime(2008, 12, 11, 16, 00),
        end_time=datetime(2008, 12, 11, 16, 45),
    )

    e = Event.objects.create(event_type=play_type, title="alpha", group=g)
    Occurrence.objects.create(
        event=e,
        start_time=datetime(2008, 12, 11, 15, 30),
        end_time=datetime(2008, 12, 11, 17, 45),
    )

    e = Event.objects.create(event_type=work_type, title="zelda", group=g)
    Occurrence.objects.create(
        event=e,
        start_time=datetime(2008, 12, 11, 15, 15),
        end_time=datetime(2008, 12, 11, 15, 45),
    )

    e = Event.objects.create(event_type=play_type, title="delta", group=g)
    Occurrence.objects.create(
        event=e,
        start_time=datetime(2008, 12, 11, 16, 30),
        end_time=datetime(2008, 12, 11, 17, 15),
    )

    return Event.objects.all()
