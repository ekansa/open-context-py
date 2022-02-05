from django.http import HttpResponse


# These views display an HTML form for classifying import fields,
# and handles AJAX requests / responses to change classifications
def index(request):
    return HttpResponse("Hello, world. You're at the entities index.")
