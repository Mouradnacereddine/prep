from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from ..models import Site, Unite, Train, Equipement, Article
from .serializers import (
    SiteSerializer,
    UniteSerializer,
    TrainSerializer,
    EquipementSerializer,
    ArticleSerializer
)

@api_view(['GET'])
def api_root(request):
    return Response({
        'sites': '/api/sites/',
        'unites': '/api/unites/',
        'trains': '/api/trains/',
        'equipements': '/api/equipements/',
        'articles': '/api/articles/',
    })

class SiteViewSet(viewsets.ModelViewSet):
    queryset = Site.objects.all()
    serializer_class = SiteSerializer
    permission_classes = [AllowAny]  # Permettre l'accès anonyme

class UniteViewSet(viewsets.ModelViewSet):
    queryset = Unite.objects.all()
    serializer_class = UniteSerializer
    permission_classes = [AllowAny]  # Permettre l'accès anonyme

class TrainViewSet(viewsets.ModelViewSet):
    queryset = Train.objects.all()
    serializer_class = TrainSerializer
    permission_classes = [AllowAny]  # Permettre l'accès anonyme

class EquipementViewSet(viewsets.ModelViewSet):
    queryset = Equipement.objects.all()
    serializer_class = EquipementSerializer
    permission_classes = [AllowAny]  # Permettre l'accès anonyme

class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [AllowAny]  # Permettre l'accès anonyme
