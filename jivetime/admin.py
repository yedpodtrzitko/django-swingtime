from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline

from .models import Event, EventGroup, EventType, Note, Occurrence


class EventTypeAdmin(admin.ModelAdmin):
    list_display = ("label", "abbr")


class OccurrenceInline(admin.TabularInline):
    model = Occurrence
    extra = 1


class EventNoteInline(GenericTabularInline):
    model = Note
    extra = 1


class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "event_type", "description")
    list_filter = ("event_type",)
    search_fields = ("title", "description")
    inlines = [EventNoteInline, OccurrenceInline]


admin.site.register(EventGroup)
admin.site.register(Event, EventAdmin)
admin.site.register(EventType, EventTypeAdmin)
