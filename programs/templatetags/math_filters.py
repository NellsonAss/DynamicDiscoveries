from django import template

register = template.Library()


@register.filter
def multiply(value, arg):
    """
    Multiply the value by the argument.
    Usage: {{ value|multiply:arg }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def divide(value, arg):
    """
    Divide the value by the argument.
    Usage: {{ value|divide:arg }}
    """
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def subtract(value, arg):
    """
    Subtract the argument from the value.
    Usage: {{ value|subtract:arg }}
    """
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def percentage(value, arg):
    """
    Calculate percentage: (value / arg) * 100
    Usage: {{ value|percentage:arg }}
    """
    try:
        if float(arg) == 0:
            return 0
        return (float(value) / float(arg)) * 100
    except (ValueError, TypeError):
        return 0 