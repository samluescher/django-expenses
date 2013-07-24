# coding=utf-8
from django.utils.translation import ugettext_lazy as _
from django import template
from django.utils.encoding import force_unicode
from django.template.defaultfilters import floatformat as django_floatformat

def floatformat(value, decimals):
    return django_floatformat(value, decimals).replace('-', u'−')

def percent(float_value, unit=u'%s%%'):
    if float_value == None:
        return ''
    rounded = floatformat(float_value * 100, 2)
    return unit % force_unicode(rounded)

def money(value, unit=u''):
    rounded = floatformat(value, 2)
    if not unit or value is None:
        return rounded
    return _(unit) % rounded

register = template.Library()
register.filter('money', money)
register.filter('percent', percent)
