from datetime import datetime, timezone

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User

from jivetime.models import Event, EventGroup, EventType, Occurrence

GROUP_DEFAULT_ID = 1


@pytest.fixture
def group_default():
    def create_group(**kwargs):
        # OwnerClass = settings.AUTH_USER_MODEL
        OwnerClass = get_user_model()
        owner, _ = OwnerClass.objects.get_or_create(username="test")
        defaults = {
            "owner": owner,
            "name": "testing group",
        }
        defaults.update(kwargs)
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
def occurrence(work_type, group_default):
    e = Event.objects.create(
        event_type=work_type,
        title="event",
        group=group_default(),
        url="https://example.com/occ/",
    )
    return Occurrence.objects.create(
        event=e,
        start_time=datetime(2018, 3, 18, 16, 00, tzinfo=timezone.utc),
        end_time=datetime(2018, 3, 18, 16, 45, tzinfo=timezone.utc),
    )


@pytest.fixture
def events(play_type, work_type, group_default):
    owner = User.objects.create_user("test_user")
    g = group_default(owner=owner)

    e = Event.objects.create(event_type=play_type, title="bravo", group=g)
    Occurrence.objects.create(
        event=e,
        start_time=datetime(2008, 12, 11, 16, 00, tzinfo=timezone.utc),
        end_time=datetime(2008, 12, 11, 16, 45, tzinfo=timezone.utc),
    )

    e = Event.objects.create(event_type=work_type, title="echo", group=g)
    Occurrence.objects.create(
        event=e,
        start_time=datetime(2008, 12, 11, 17, 15, tzinfo=timezone.utc),
        end_time=datetime(2008, 12, 11, 18, 00, tzinfo=timezone.utc),
    )

    e = Event.objects.create(event_type=play_type, title="charlie", group=g)
    Occurrence.objects.create(
        event=e,
        start_time=datetime(2008, 12, 11, 16, 15, tzinfo=timezone.utc),
        end_time=datetime(2008, 12, 11, 17, 00, tzinfo=timezone.utc),
    )

    e = Event.objects.create(event_type=work_type, title="foxtrot", group=g)
    Occurrence.objects.create(
        event=e,
        start_time=datetime(2008, 12, 11, 16, 00, tzinfo=timezone.utc),
        end_time=datetime(2008, 12, 11, 16, 45, tzinfo=timezone.utc),
    )

    e = Event.objects.create(event_type=play_type, title="alpha", group=g)
    Occurrence.objects.create(
        event=e,
        start_time=datetime(2008, 12, 11, 15, 30, tzinfo=timezone.utc),
        end_time=datetime(2008, 12, 11, 17, 45, tzinfo=timezone.utc),
    )

    e = Event.objects.create(event_type=work_type, title="zelda", group=g)
    Occurrence.objects.create(
        event=e,
        start_time=datetime(2008, 12, 11, 15, 15, tzinfo=timezone.utc),
        end_time=datetime(2008, 12, 11, 15, 45, tzinfo=timezone.utc),
    )

    e = Event.objects.create(event_type=play_type, title="delta", group=g)
    Occurrence.objects.create(
        event=e,
        start_time=datetime(2008, 12, 11, 16, 30, tzinfo=timezone.utc),
        end_time=datetime(2008, 12, 11, 17, 15, tzinfo=timezone.utc),
    )

    return Event.objects.all()
