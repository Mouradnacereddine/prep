from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.permissions import IsAuthenticated, AllowAny
from gestion_prep.models import Site, Unite, Train, Equipement, Article
from ..serializers import (
    SiteSerializer,
    UniteSerializer,
    TrainSerializer,
    EquipementSerializer,
    ArticleSerializer
)
from .auth import UserMeView

@api_view(['GET'])
def api_root(request, format=None):
    return Response({
        'users-me': reverse('user-me', request=request, format=format),
        'sites': reverse('site-list', request=request, format=format),
        'unites': reverse('unite-list', request=request, format=format),
        'trains': reverse('train-list', request=request, format=format),
        'equipements': reverse('equipement-list', request=request, format=format),
        'articles': reverse('article-list', request=request, format=format),
    })

class SiteViewSet(viewsets.ModelViewSet):
    queryset = Site.objects.all()
    serializer_class = SiteSerializer
    permission_classes = [AllowAny]

class UniteViewSet(viewsets.ModelViewSet):
    queryset = Unite.objects.all()
    serializer_class = UniteSerializer
    permission_classes = [AllowAny]

class TrainViewSet(viewsets.ModelViewSet):
    queryset = Train.objects.all()
    serializer_class = TrainSerializer
    permission_classes = [AllowAny]

class EquipementViewSet(viewsets.ModelViewSet):
    queryset = Equipement.objects.all()
    serializer_class = EquipementSerializer
    permission_classes = [AllowAny]

class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [AllowAny]

__all__ = [
    'api_root',
    'SiteViewSet',
    'UniteViewSet',
    'TrainViewSet',
    'EquipementViewSet',
    'ArticleViewSet',
    'UserMeView',
]