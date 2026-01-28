from django.shortcuts import render

def _get_error_redirect_context(request):
    is_admin = request.path.startswith("/admin")

    if is_admin:
        return {
            "home_url": "/admin/dashboard/",
            "home_label": "Go to Admin Dashboard",
            "is_admin": True,
        }
    else:
        return {
            "home_url": "/home/",
            "home_label": "Go to Home",
            "is_admin": False,
        }


def error_400(request, exception):
    context = _get_error_redirect_context(request)
    return render(request, "errors/400.html", context, status=400)

def error_404(request, exception):
    context = _get_error_redirect_context(request)
    return render(request, 'errors/404.html', context, status=404)

def error_500(request):
    context = _get_error_redirect_context(request)
    return render(request, 'errors/500.html', context, status=500)

def error_403(request, exception=None):
    context = _get_error_redirect_context(request)
    return render(request, 'errors/403.html', context, status=403)
