import os

from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter
@stringfilter
def sep_replace(path):
    """replace value from s"""
    return path.replace(os.sep, "/")
