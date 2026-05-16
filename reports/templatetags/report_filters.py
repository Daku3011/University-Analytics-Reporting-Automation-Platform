from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, 0)

@register.filter
def first(value):
    if isinstance(value, (list, tuple)) and value:
        return value[0]
    return 0
