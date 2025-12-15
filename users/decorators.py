from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse,HttpResponse
def block_check(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_blocked:
            logout(request)
            messages.error(request, "Your account has been blocked by admin.")

            if request.headers.get('HX-Request'):
                # response = JsonResponse({'blocked': True, 'redirect_url': '/login/'})
                # response['HX-Location'] = '/login/'   
                # return response
                return HttpResponse(
                    '<script>window.location.href="/login/";</script>'
                )

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'blocked': True,
                    'message': 'Your account is blocked',
                    'redirect_url': '/login/'
                }, status=403)

            return redirect('user_login')

        return view_func(request, *args, **kwargs)
    return wrapper
