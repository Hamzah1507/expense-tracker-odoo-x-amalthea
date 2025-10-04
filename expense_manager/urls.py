from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect


# ✅ Home view: decides where to go based on authentication
def home(request):
    if request.user.is_authenticated:
        # Redirect authenticated users to dashboard
        return redirect('dashboard')
    else:
        # Redirect unauthenticated users to login page
        return redirect('login')


urlpatterns = [
    # Django Admin Panel
    path('admin/', admin.site.urls),

    # API endpoints
    path('api/users/', include('users.urls')),
    path('api/', include('expenses.urls')),

    # Frontend (Template) routes
    path('app/', include('expenses.frontend_urls')),

    # Root route ("/") → handled by home() defined above
    path('', home, name='home'),
]
