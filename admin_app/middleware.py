from django.shortcuts import redirect
from django.urls import resolve

class AdminAlreadyLoggedInRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/admin/":
            if request.user.is_authenticated and request.user.is_staff:
                return redirect("/admin/dashboard/")

        return self.get_response(request)
