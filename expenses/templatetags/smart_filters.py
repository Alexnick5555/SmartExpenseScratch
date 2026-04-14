import json
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(is_safe=True)
def safe_json(value):
    if value is None:
        return 'null'
    try:
        return mark_safe(json.dumps(value))
    except (TypeError, ValueError):
        return 'null'


@register.filter
def split(value, delimiter=','):
    return value.split(delimiter)
