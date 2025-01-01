from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse
from django.views.decorators.http import require_GET

@require_GET
@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({'detail': 'CSRF cookie set'})

urlpatterns = [
    # CSRF endpoint
    path('csrf/', get_csrf_token, name='csrf_token'),
    
    # Auth endpoints
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', views.verify_token, name='verify_token'),
    
    # Password management
    path('password/reset/', views.request_password_reset, name='password_reset_request'),
    path('password/reset/<uidb64>/<token>/verify/', views.verify_reset_token, name='password_reset_verify'),
    path('password/reset/<uidb64>/<token>/confirm/', views.reset_password, name='password_reset_confirm'),
    path('password/change/', views.change_password, name='change_password'),
    
    # Profile management
    path('profile/', views.get_profile, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    
    # Email verification
    path('verify-email/resend/', views.resend_verification, name='resend_verification'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    
    # Department management
    path('department/users/', views.list_department_users, name='department_users'),
    path('department/assign-manager/<int:user_id>/', views.assign_manager_role, name='assign_manager'),
    path('department/remove-manager/<int:user_id>/', views.remove_manager_role, name='remove_manager'),
    path('department/stats/', views.department_stats, name='department_stats'),
    
    # Admin
    path('users/', views.list_all_users, name='list_all_users'),
]
