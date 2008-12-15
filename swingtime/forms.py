'''
Convenience forms for adding and updating ``Event`` and ``Occurrence``s.

'''
from datetime import datetime, date, time, timedelta

from django import forms
from django.forms.extras.widgets import SelectDateWidget

from dateutil import rrule
from swingtime.conf import settings as swingtime_settings
from swingtime import utils
from swingtime.models import *



WEEKDAY_SHORT = (
    (7, 'Sun'),
    (1, 'Mon'),
    (2, 'Tue'),
    (3, 'Wed'),
    (4, 'Thu'),
    (5, 'Fri'),
    (6, 'Sat')
)

WEEKDAY_LONG = (
    (7, 'Sunday'),
    (1, 'Monday'),
    (2, 'Tuesday'),
    (3, 'Wednesday'),
    (4, 'Thursday'),
    (5, 'Friday'),
    (6, 'Saturday')
)

MONTH_LONG = (
    (1,  'January'),
    (2,  'February'),
    (3,  'March'),
    (4,  'April'),
    (5,  'May'),
    (6,  'June'),
    (7,  'July'),
    (8,  'August'),
    (9,  'September'),
    (10, 'October'),
    (11, 'November'),
    (12, 'December'),
)


ORDINAL = (
    (1,  'first'),
    (2,  'second'),
    (3,  'third'),
    (4,  'fourth'),
    (-1, 'last')
)

FREQUENCY_CHOICES = (
    (rrule.DAILY,   'Day(s)'),
    (rrule.WEEKLY,  'Week(s)'),
    (rrule.MONTHLY, 'Month(s)'),
    (rrule.YEARLY,  'Year(s)'),
)

REPEAT_CHOICES = (
    ('count', 'By count'),
    ('until', 'Until date'),
)

ISO_WEEKDAYS_MAP = (
    None,
    rrule.MO,
    rrule.TU,
    rrule.WE,
    rrule.TH,
    rrule.FR,
    rrule.SA,
    rrule.SU
)


#-------------------------------------------------------------------------------
def timeslot_options(
    interval=swingtime_settings.TIMESLOT_INTERVAL,
    start_time=swingtime_settings.TIMESLOT_START_TIME,
    end_delta=swingtime_settings.TIMESLOT_END_TIME_DELTA,
    fmt=swingtime_settings.TIMESLOT_TIME_FORMAT
):
    '''
    Create a list of time slot options for use in swingtime forms.
    
    The list is comprised of 2-tuples containing a 24-hour time value and a 
    12-hour temporal representation of that offset.
    
    '''
    dt = datetime.combine(date.today(), time(0))
    dtstart = datetime.combine(dt.date(), start_time)
    dtend = dtstart + end_delta
    options = []

    while dtstart <= dtend:
        options.append((str(dtstart.time()), dtstart.strftime(fmt)))
        dtstart += interval
    
    return options

#-------------------------------------------------------------------------------
def timeslot_offset_options(
    interval=swingtime_settings.TIMESLOT_INTERVAL,
    start_time=swingtime_settings.TIMESLOT_START_TIME,
    end_delta=swingtime_settings.TIMESLOT_END_TIME_DELTA,
    fmt=swingtime_settings.TIMESLOT_TIME_FORMAT
):
    '''
    Create a list of time slot options for use in swingtime forms.
    
    The list is comprised of 2-tuples containing the number of seconds since the
    start of the day and a 12-hour temporal representation of that offset.
    
    '''
    dt = datetime.combine(date.today(), time(0))
    dtstart = datetime.combine(dt.date(), start_time)
    dtend = dtstart + end_delta
    options = []

    delta = utils.time_delta_total_seconds(dtstart - dt)
    seconds = utils.time_delta_total_seconds(interval)
    while dtstart <= dtend:
        options.append((delta, dtstart.strftime(fmt)))
        dtstart += interval
        delta += seconds
    
    return options

default_timeslot_options = timeslot_options()
default_timeslot_offset_options = timeslot_offset_options()


#===============================================================================
class MultipleIntegerField(forms.MultipleChoiceField):
    '''
    A form field for handling multiple integers.
    
    '''
    
    #---------------------------------------------------------------------------
    def __init__(self, choices, size=None, label=None):
        size = size or len(choices)
        super(MultipleIntegerField, self).__init__(
            required=False,
            choices=choices,
            label=label,
            widget=forms.SelectMultiple(attrs={'size' : size}),
        )

    #---------------------------------------------------------------------------
    def clean(self, value):
        return [int(i) for i in super(MultipleIntegerField, self).clean(value)]


#===============================================================================
class SplitDateTimeWidget(forms.MultiWidget):
    '''
    A Widget that splits datetime input into a SelectDateWidget for dates and
    Select widget for times.
    
    '''
    #---------------------------------------------------------------------------
    def __init__(self, attrs=None):
        widgets = (
            SelectDateWidget(attrs=attrs), 
            forms.Select(choices=default_timeslot_options, attrs=attrs)
        )
        super(SplitDateTimeWidget, self).__init__(widgets, attrs)

    #---------------------------------------------------------------------------
    def decompress(self, value):
        if value:
            return [value.date(), value.time().replace(microsecond=0)]
        
        return [None, None]


#===============================================================================
class MultipleOccurrenceForm(forms.Form):
    day = forms.DateField(
        label='Date',
        initial=date.today,
        widget=SelectDateWidget()
    )
    
    start_time_delta = forms.IntegerField(
        label='Start time',
        widget=forms.Select(choices=default_timeslot_offset_options)
    )
    
    end_time_delta = forms.IntegerField(
        label='End time',
        widget=forms.Select(choices=default_timeslot_offset_options)
    )

    # recurrence options
    repeats = forms.ChoiceField(
        choices=REPEAT_CHOICES,
        initial='count',
        label='Occurrences',
        widget=forms.RadioSelect()
    )

    count = forms.IntegerField(
        label='Total Occurrences',
        initial=1,
        required=False,
        widget=forms.TextInput(attrs=dict(size=2, max_length=2))
    )

    until = forms.DateField(
        required=False,
        initial=date.today,
        widget=SelectDateWidget()
    )
    
    freq = forms.IntegerField(
        label='Frequency',
        initial=rrule.WEEKLY,
        widget=forms.Select(choices=FREQUENCY_CHOICES)
    )

    interval = forms.IntegerField(
        required=False,
        initial='1',
        widget=forms.TextInput(attrs=dict(size=3, max_length=3))
    )
    
    # weekly options
    week_days = MultipleIntegerField(WEEKDAY_LONG, label='Weekly options')
    
    # monthly  options
    month_option = forms.ChoiceField(
        choices=(('on','On the'), ('each','Each:')),
        initial='each',
        widget=forms.RadioSelect(),
        label='Monthly options'
    )
    
    month_ordinal = forms.IntegerField(widget=forms.Select(choices=ORDINAL))
    month_ordinal_day = forms.IntegerField(widget=forms.Select(choices=WEEKDAY_LONG))
    each_month_day = MultipleIntegerField([(i,i) for i in range(1,32)], 10)
    
    # yearly options
    year_months = MultipleIntegerField(MONTH_LONG, label='Yearly options')
    is_year_month_ordinal = forms.BooleanField(required=False)
    year_month_ordinal = forms.IntegerField(widget=forms.Select(choices=ORDINAL))
    year_month_ordinal_day = forms.IntegerField(widget=forms.Select(choices=WEEKDAY_LONG))
    
    #---------------------------------------------------------------------------
    def __init__(self, *args, **kws):
        super(MultipleOccurrenceForm, self).__init__(*args, **kws)
    
    #---------------------------------------------------------------------------
    def clean(self):
        day = datetime.combine(self.cleaned_data['day'], time(0))
        self.cleaned_data['start_time'] = day + timedelta(
            seconds=self.cleaned_data['start_time_delta']
        )
        
        self.cleaned_data['end_time'] = day + timedelta(
            seconds=self.cleaned_data['end_time_delta']
        )
        
        return self.cleaned_data

    #---------------------------------------------------------------------------
    def save(self, event):
        if self.cleaned_data['repeats'] == 'no':
            params = {}
        else:
            params = self._build_rrule_params()

        event.add_occurrences(
            self.cleaned_data['start_time'], 
            self.cleaned_data['end_time'],
            **params
        )

        return event

    #---------------------------------------------------------------------------
    def _build_rrule_params(self):
        iso = ISO_WEEKDAYS_MAP
        data = self.cleaned_data
        params = dict(
            freq=data['freq'],
            #dtstart=data['start_time'],
            interval=data['interval'] or 1
        )
        
        if self.cleaned_data['repeats'] == 'count':
            params['count'] = data['count']
        elif self.cleaned_data['repeats'] == 'until':
            params['until'] = data['until']

        if params['freq'] == rrule.WEEKLY:
            params['byweekday'] = [iso[n] for n in data['week_days']]

        elif params['freq'] == rrule.MONTHLY:
            if 'on' == data['month_option']:
                ordinal = data['month_ordinal']
                day = iso[data['month_ordinal_day']]
                params['byweekday'] = day(ordinal)
            else:
                params['bymonthday'] = data['each_month_day']

        elif params['freq'] == rrule.YEARLY:
            params['bymonth'] = data['year_months']
            if data['is_year_month_ordinal']:
                ordinal = data['year_month_ordinal']
                day = iso[data['year_month_ordinal_day']]
                params['byweekday'] = day(ordinal)
                
        elif params['freq'] != rrule.DAILY:
            raise NotImplementedError('Unknown interval rule %s' % params['freq'])

        return params


#===============================================================================
class NewEventForm(MultipleOccurrenceForm):
    event_type = forms.ModelChoiceField(EventType.objects)
    
    title = forms.CharField(
        max_length=32,
        widget=forms.TextInput(attrs=dict(size=32))
    )
    
    description = forms.CharField(
        label='Description', 
        required=False, 
        max_length=100,
        widget=forms.TextInput(attrs=dict(size=50)),
    )

    #---------------------------------------------------------------------------
    def save(self):
        event = Event.objects.create(
            title=self.cleaned_data['title'], 
            event_type=self.cleaned_data['event_type'],
            description=self.cleaned_data['description']
        )
        
        super(NewEventForm, self).save(self)
        return event


#===============================================================================
class EventForm(forms.ModelForm):
    
    #===========================================================================
    class Meta:
        model = Event


#===============================================================================
class SingleOccurrenceForm(forms.ModelForm):
    start_time = forms.DateTimeField(widget=SplitDateTimeWidget)
    end_time = forms.DateTimeField(widget=SplitDateTimeWidget)
    
    #===========================================================================
    class Meta:
        model = Occurrence
        

