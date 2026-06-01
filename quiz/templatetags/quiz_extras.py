from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    return mapping.get(key)


@register.filter
def div(value, divisor):
    try:
        return float(value) / float(divisor)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0


@register.filter
def percent_of(value, total):
    try:
        total = float(total)
        if total <= 0:
            return 0
        return round((float(value) / total) * 100, 2)
    except (TypeError, ValueError):
        return 0


@register.filter
def duration_hms(seconds):
    try:
        seconds = max(0, int(seconds))
    except (TypeError, ValueError):
        seconds = 0
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
