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


@register.filter
def replace(value, old, new=''):
    """Replace all occurrences of old with new in the string."""
    if value is None:
        return ''
    return str(value).replace(old, new)
