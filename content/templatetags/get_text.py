from django import template

from content.models import Text


register = template.Library()


@register.simple_tag
def get_text_for(place):
    if place not in Text.PLACE._ALL:
        msg = 'Wrong text place: %s; choices are %s.'
        raise ValueError(msg % (place, ', '.join(Text.PLACE._ALL)))
    try:
        return Text.objects.active().get(place=place).text
    except Text.DoesNotExist:
        return ''
