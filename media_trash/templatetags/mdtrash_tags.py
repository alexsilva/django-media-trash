import os

from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter
@stringfilter
def sep_replace(path):
    """replace value from s"""
    return path.replace(os.sep, "/")


@register.simple_tag
def get_bootstrap_alert_tags(tags):
    return 'danger' if tags == 'error' else tags
