from django.core.management.base import BaseCommand
from gestion_prep.models import Site, Unite, Train, Equipement, Article, Stock, CategorieArticle

class Command(BaseCommand):
    help = 'Crée des données de test pour l\'application'

    def handle(self, *args, **kwargs):
        # Création d'un site
        site = Site.objects.create(
            nom="Site Principal",
            description="Site principal de test"
        )
        self.stdout.write(self.style.SUCCESS(f'Site créé: {site.nom}'))

        # Création d'une unité
        unite = Unite.objects.create(
            nom="Unité 1",
            site=site,
            description="Première unité de test"
        )
        self.stdout.write(self.style.SUCCESS(f'Unité créée: {unite.nom}'))

        # Création d'un train
        train = Train.objects.create(
            nom="Train A",
            unite=unite,
            description="Premier train de test"
        )
        self.stdout.write(self.style.SUCCESS(f'Train créé: {train.nom}'))

        # Création d'un équipement
        equipement = Equipement.objects.create(
            tag="EQ001",
            description="Premier équipement de test",
            train=train
        )
        self.stdout.write(self.style.SUCCESS(f'Équipement créé: {equipement.tag}'))

        # Création d'un stock
        stock = Stock.objects.create(
            nom="Magasin Principal",
            site=site,
            type_stock="MAGASIN",
            emplacement="Zone A",
            description="Stock principal de test"
        )
        self.stdout.write(self.style.SUCCESS(f'Stock créé: {stock.nom}'))

        # Création d'une catégorie d'article
        categorie = CategorieArticle.objects.create(
            nom="Catégorie 1",
            description="Première catégorie de test"
        )
        self.stdout.write(self.style.SUCCESS(f'Catégorie créée: {categorie.nom}'))

        # Création d'articles
        articles = [
            {
                "code_article": "ART001",
                "description": "Premier article de test",
                "specification": "Spécification de test",
                "stock": stock,
                "categorie_article": categorie,
                "unite_mesure": "PCE",
                "quantite_initiale": 100,
                "quantite_stock": 100,
                "seuil_alerte": 20
            },
            {
                "code_article": "ART002",
                "description": "Deuxième article de test",
                "specification": "Spécification de test 2",
                "stock": stock,
                "categorie_article": categorie,
                "unite_mesure": "PCE",
                "quantite_initiale": 50,
                "quantite_stock": 50,
                "seuil_alerte": 10
            }
        ]

        for article_data in articles:
            article = Article.objects.create(**article_data)
            self.stdout.write(self.style.SUCCESS(f'Article créé: {article.code_article}'))
