from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

# Home view
def home(request):
    return JsonResponse({"message": "Expense Manager API is running"})

urlpatterns = [
    path("", home, name="home"),  # Root path
    path('admin/', admin.site.urls),
    path("api/users/", include("users.urls")),
]
