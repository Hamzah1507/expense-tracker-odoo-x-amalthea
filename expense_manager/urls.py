from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

# Home view
def home(request):
    from django.shortcuts import redirect
    if request.user.is_authenticated:
        return redirect('dashboard')
    else:
        return redirect('login')

urlpatterns = [
    path("", home, name="home"),  # Root path
    path('admin/', admin.site.urls),
    path("api/users/", include("users.urls")),
    path("api/", include("expenses.urls")),
    path("", include("expenses.frontend_urls")),  # Frontend routes
]
