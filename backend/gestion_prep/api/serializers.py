from rest_framework import serializers
from ..models import Site, Unite, Train, Equipement, Article

class SiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = ["id", "nom", "description"]

class UniteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unite
        fields = ["id", "nom", "site", "description"]

class TrainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Train
        fields = ["id", "nom", "unite", "description"]

class EquipementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipement
        fields = ["id", "tag", "description", "train"]

class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = [
            'id', 
            'code_article', 
            'description', 
            'specification',
            'stock',
            'categorie_article',
            'unite_mesure',
            'quantite_initiale',
            'quantite_stock',
            'seuil_alerte'
        ]
