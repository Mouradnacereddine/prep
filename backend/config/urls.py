from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.views.static import serve
from django.http import HttpResponse

def favicon_view(request):
    return HttpResponse(status=204)

urlpatterns = [
    # Route pour éviter l'erreur 404 favicon
    path('favicon.ico', favicon_view),
    
    # Rediriger la racine vers l'admin
    path('', RedirectView.as_view(url='/admin/', permanent=True)),
    
    # Interface d'administration Django
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/', include('gestion_prep.api.urls')),
    path('api-auth/', include('rest_framework.urls')),
    path('api/auth/', include('user_auth.urls')),
    
    # Media files
    path('media/<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
