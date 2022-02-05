from django.http import HttpResponse


# These views handle requests for interacting with the version history
def index(request):
    return HttpResponse("Hello, world. You're at the versioning index.")

