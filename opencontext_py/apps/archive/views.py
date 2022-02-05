from django.http import HttpResponse


def index(request, spatial_context=None):
    return HttpResponse("Hello, world. You're at the archive index.")
