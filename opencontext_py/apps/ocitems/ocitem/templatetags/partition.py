from django import template
register = template.Library()


@register.filter(name='columns')
def columns(thelist, n):
    """ Splits a list into a list of lists with 'n' columns """
    try:
        n = int(n)
        thelist = list(thelist)
    except (ValueError, TypeError):
        return [thelist]
    list_len = len(thelist)
    split = list_len // n
    if list_len % n != 0:
        split += 1
    return [thelist[i::split] for i in range(split)]
