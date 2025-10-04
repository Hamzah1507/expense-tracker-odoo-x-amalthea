from django.http import JsonResponse

def login_view(request):
    return JsonResponse({"message": "Login endpoint working"})

def signup_view(request):
    return JsonResponse({"message": "Signup endpoint working"})

def profile_view(request):
    return JsonResponse({"message": "Profile endpoint working"})
