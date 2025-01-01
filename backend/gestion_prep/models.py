from typing import Any, Optional, cast, Type, ClassVar, TypeVar, Union, Dict, List, Callable
from typing_extensions import TypedDict, NotRequired
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import F, Q, QuerySet, Manager
from django.db.models.manager import Manager
from django.db.models.fields.related_descriptors import ReverseManyToOneDescriptor
from django.db.models.fields.files import FieldFile
from django.core.validators import MinValueValidator
from django.db import transaction

T = TypeVar('T', bound=models.Model)

UserModel = get_user_model()

class DjangoModel(models.Model):
    """Base model class with proper type hints for Django ORM."""
    objects: Manager['DjangoModel'] = models.Manager()  # type: ignore

    class Meta:
        abstract = True

class Site(DjangoModel):
    """Model representing a site."""
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self) -> str:
        return str(self.nom)

    class Meta(DjangoModel.Meta):
        ordering = ['nom']
        verbose_name = _('Site')
        verbose_name_plural = _('Sites')

class Unite(DjangoModel):
    """Model representing a unit."""
    nom = models.CharField(max_length=100)
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='unites'
    )
    description = models.TextField(blank=True, null=True)

    def __str__(self) -> str:
        site_obj = cast(Site, self.site)
        return f"{str(site_obj.nom)} - {str(self.nom)}" if self.site else str(self.nom)

    class Meta(DjangoModel.Meta):
        ordering = ['site__nom', 'nom']
        verbose_name = _('Unité')
        verbose_name_plural = _('Unités')
        unique_together = ['site', 'nom']

class Train(DjangoModel):
    """Model representing a train."""
    nom = models.CharField(max_length=100)
    unite = models.ForeignKey(
        Unite,
        on_delete=models.CASCADE,
        related_name='trains',
        null=False,
        blank=False
    )
    description = models.TextField(blank=True, null=True)

    def __str__(self) -> str:
        unite_obj = cast(Unite, self.unite)
        return f"{str(unite_obj.nom)} - {str(self.nom)}" if self.unite else str(self.nom)

    class Meta(DjangoModel.Meta):
        ordering = ['unite__site__nom', 'unite__nom', 'nom']
        verbose_name = _('Train')
        verbose_name_plural = _('Trains')
        unique_together = ['unite', 'nom']

class Equipement(DjangoModel):
    """Model representing an equipment."""
    tag = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    train = models.ForeignKey(
        Train,
        on_delete=models.CASCADE,
        related_name='equipements'
    )

    def __str__(self) -> str:
        if not self.train:
            return f"{str(self.tag)} - {str(self.description)}"
        
        train_obj = cast(Train, self.train)
        unite_obj = cast(Unite, train_obj.unite)
        site_obj = cast(Site, unite_obj.site)
        
        return (
            f"{str(self.tag)} - {str(self.description)} | "
            f"Site: {str(site_obj.nom)} | "
            f"Unité: {str(unite_obj.nom)} | "
            f"Train: {str(train_obj.nom)}"
        )

    class Meta(DjangoModel.Meta):
        ordering = ['tag']
        verbose_name = _('Equipement')
        verbose_name_plural = _('Equipements')

class CategorieArticle(DjangoModel):
    """Model representing an article category."""
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self) -> str:
        return str(self.nom)

    class Meta(DjangoModel.Meta):
        verbose_name = _('Catégorie d\'article')
        verbose_name_plural = _('Catégories d\'articles')
        ordering = ['nom']

class Stock(DjangoModel):
    """Model representing a stock."""
    TYPE_STOCK_CHOICES = [
        ('MAGASIN', 'Magasin'),
        ('HORS_MAGASIN', 'Hors Magasin'),
    ]

    nom = models.CharField(max_length=100)
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='stocks'
    )
    type_stock = models.CharField(
        max_length=20,
        choices=TYPE_STOCK_CHOICES,
        default='MAGASIN'
    )
    description = models.TextField(blank=True, null=True)
    emplacement = models.CharField(max_length=100, blank=False, null=False)

    def __str__(self) -> str:
        return f"{self.nom} - {self.emplacement}"

    class Meta(DjangoModel.Meta):
        ordering = ['nom']
        verbose_name = _('Stock')
        verbose_name_plural = _('Stocks')
        unique_together = ['nom', 'type_stock', 'emplacement']

class Article(DjangoModel):
    """Model representing an article."""
    code_article = models.CharField(max_length=100)
    description = models.TextField()
    specification = models.TextField(blank=True, null=True)
    prix = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Prix')
    )
    devise = models.CharField(
        max_length=3,
        choices=[
            ('EUR', 'Euro (€)'),
            ('USD', 'Dollar ($)'),
            ('GBP', 'Livre Sterling (£)'),
            ('DZD', 'Dinar Algérien (DZD)'),
        ],
        null=True,
        blank=True,
        verbose_name=_('Devise')
    )
    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name='articles'
    )
    categorie_article = models.ForeignKey(
        CategorieArticle,
        on_delete=models.CASCADE,
        related_name='articles'
    )
    unite_mesure = models.CharField(max_length=20)
    quantite_initiale = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=False,
        validators=[MinValueValidator(0)]
    )
    quantite_stock = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=False,
        validators=[MinValueValidator(0)]
    )
    seuil_alerte = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=False,
        validators=[MinValueValidator(0)]
    )

    class Meta(DjangoModel.Meta):
        ordering = ['code_article']
        verbose_name = _('Article')
        verbose_name_plural = _('Articles')
        unique_together = ['code_article', 'stock']

    def clean(self):
        super().clean()
        if self.prix is not None and not self.devise:
            raise ValidationError({
                'devise': _('La devise est obligatoire lorsqu\'un prix est spécifié.')
            })

    def __str__(self) -> str:
        if not self.stock or not self.categorie_article:
            return f"{self.code_article} - {self.description}"
            
        description_short = str(self.description)
        if len(description_short) > 50:
            description_short = description_short[:50] + "..."
            
        stock_obj = cast(Stock, self.stock)
        categorie_obj = cast(CategorieArticle, self.categorie_article)
            
        return (
            f"{self.code_article} - {description_short} | "
            f"Stock: {self.quantite_stock} {self.unite_mesure} | "
            f"Emplacement: {stock_obj.nom} ({stock_obj.emplacement}) | "
            f"Catégorie: {categorie_obj.nom}"
        )

class Phase(DjangoModel):
    """Model representing a phase in the platinage process."""
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    platinages = models.ManyToManyField(
        'Platinage',
        related_name='phases',
        verbose_name=_('Platinages'),
        blank=True
    )

    def __str__(self) -> str:
        return str(self.nom)

    class Meta(DjangoModel.Meta):
        ordering = ['nom']
        verbose_name = _('Phase')
        verbose_name_plural = _('Phases')

class TypePlatinage(DjangoModel):
    """Model representing a plating type."""
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self) -> str:
        return str(self.nom)

    class Meta(DjangoModel.Meta):
        ordering = ['nom']
        verbose_name = _('Type de platinage')
        verbose_name_plural = _('Types de platinage')

class MouvementMaterielType(TypedDict):
    lignes: Manager

class MouvementMateriel(models.Model):
    STATUT_BROUILLON = 'BROUILLON'
    STATUT_VALIDE = 'VALIDE'
    STATUT_ANNULE = 'ANNULE'
    
    STATUT_CHOICES = [
        (STATUT_BROUILLON, _('Brouillon')),
        (STATUT_VALIDE, _('Validé')),
        (STATUT_ANNULE, _('Annulé')),
    ]

    numero_bmm = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Numéro BMM'),
        editable=False
    )
    
    TYPE_SORTIE_DEFINITIVE = 'SORTIE_DEFINITIVE'
    TYPE_SORTIE_PRET = 'SORTIE_PRET'
    TYPE_ENTREE = 'ENTREE'
    
    TYPE_CHOICES = [
        (TYPE_SORTIE_DEFINITIVE, _('Sortie définitive')),
        (TYPE_SORTIE_PRET, _('Sortie à titre de prêt')),
        (TYPE_ENTREE, _('Entrée')),
    ]
    
    type_mouvement = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        verbose_name=_('Type de mouvement')
    )
    
    description_bmm = models.TextField(
        verbose_name=_('Description'),
        help_text=_('Description détaillée du mouvement')
    )
    
    emetteur_recepteur = models.CharField(
        max_length=100,
        verbose_name=_('Émetteur/Récepteur'),
        help_text=_('Nom de l\'émetteur ou du récepteur')
    )
    
    departement_service = models.CharField(
        max_length=100,
        verbose_name=_('Département/Service'),
        help_text=_('Département ou service concerné')
    )
    
    date_retour_prevue = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Date de retour prévue'),
        help_text=_('Obligatoire pour les sorties à titre de prêt')
    )
    
    date_retour_effective = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Date de retour effective')
    )
    
    equipement = models.ForeignKey(
        'Equipement',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_('Équipement'),
        help_text=_('Équipement concerné par le mouvement')
    )
    
    remarque = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Remarque'),
        help_text=_('Remarques ou notes supplémentaires')
    )
    
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=STATUT_BROUILLON,
        verbose_name=_('Statut')
    )
    
    created_by = models.ForeignKey(
        UserModel,
        on_delete=models.PROTECT,
        related_name='mouvements_crees',
        verbose_name=_('Créé par')
    )
    
    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Date de création')
    )
    
    validated_by = models.ForeignKey(
        UserModel,
        on_delete=models.PROTECT,
        related_name='mouvements_valides',
        null=True,
        blank=True,
        verbose_name=_('Validé par')
    )
    
    date_validation = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Date de validation')
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_statut = self.statut if self.pk else 'BROUILLON'
        self._validation_errors = False
        self._stocks_updated = False  # Nouveau flag

    @property
    def is_being_validated(self):
        """Indique si le BMM est en cours de validation."""
        return (self.statut == 'VALIDE' and 
                (self._original_statut == 'BROUILLON' or self._validation_errors))

    def set_validation_error(self, has_error=True):
        """Marque le BMM comme ayant des erreurs de validation."""
        self._validation_errors = has_error
        if has_error:
            self.statut = 'BROUILLON'

    def update_stocks(self):
        """Met à jour les stocks lors de la validation du mouvement"""
        print(f"Entering update_stocks for BMM {self.numero_bmm}")
        print(f"Current status: {self.statut}")
        
        # Éviter les doubles appels
        if self._stocks_updated:
            print("Stocks already updated, skipping...")
            return
            
        if self.statut == 'VALIDE':
            print(f"Processing stock updates for BMM {self.numero_bmm}")
            
            # Rafraîchir l'instance depuis la base de données
            with transaction.atomic():
                # Verrouiller le mouvement et ses lignes pour la mise à jour
                mouvement = MouvementMateriel.objects.select_for_update().get(pk=self.pk)
                lignes = mouvement.lignemouvement_set.select_for_update().select_related('article').all()
                
                print(f"Found {len(lignes)} lines to process")
                
                for ligne in lignes:
                    if ligne.article:
                        print(f"Processing line id: {ligne.pk}")
                        print(f"Raw quantity value: {ligne.quantite}")
                        
                        # Récupérer les dernières valeurs
                        ligne.refresh_from_db()
                        print(f"Quantity after refresh: {ligne.quantite}")
                        
                        # Récupérer l'article avec le stock le plus récent
                        article = Article.objects.select_for_update().get(pk=ligne.article.pk)
                        stock_actuel = article.quantite_stock
                        
                        print(f"Article {ligne.article.code_article}:")
                        print(f"  - Stock actuel (from DB): {stock_actuel}")
                        print(f"  - Quantité: {ligne.quantite}")
                        
                        # Calculer le nouveau stock en fonction du type de mouvement
                        if mouvement.type_mouvement in [self.TYPE_SORTIE_DEFINITIVE, self.TYPE_SORTIE_PRET]:
                            nouveau_stock = stock_actuel - ligne.quantite
                        else:  # TYPE_ENTREE
                            nouveau_stock = stock_actuel + ligne.quantite
                        
                        print(f"  - Nouveau stock calculé: {nouveau_stock}")
                        
                        # Mettre à jour l'historique des stocks dans la ligne
                        # Sauvegarder d'abord l'historique
                        ligne.stock_avant = stock_actuel
                        ligne.stock_apres = nouveau_stock
                        ligne.save(update_fields=['stock_avant', 'stock_apres'])
                        
                        # Ensuite mettre à jour le stock de l'article
                        article.quantite_stock = nouveau_stock
                        article.save(update_fields=['quantite_stock'])
                        
                        # Vérifier que la mise à jour a bien été effectuée
                        article.refresh_from_db()
                        print(f"  - Stock après mise à jour (vérifié): {article.quantite_stock}")
                
                self._stocks_updated = True

    def clean(self):
        """Validation du mouvement selon son statut"""
        super().clean()
        
        # Validation du type de mouvement et de la date de retour
        if self.type_mouvement == self.TYPE_SORTIE_PRET and not self.date_retour_prevue:
            raise ValidationError({
                'date_retour_prevue': _('La date de retour est obligatoire pour les sorties à titre de prêt.')
            })
            
        # Validation du changement de statut
        if self.pk and self._original_statut != self.statut:
            if self._original_statut == self.STATUT_VALIDE and self.statut == self.STATUT_BROUILLON:
                raise ValidationError(_('Un mouvement validé ne peut pas revenir au statut brouillon.'))
            if self._original_statut == self.STATUT_ANNULE:
                raise ValidationError(_('Un mouvement annulé ne peut pas changer de statut.'))
        
        # Empêcher la modification des champs une fois validé
        if self.pk and self._original_statut == self.STATUT_VALIDE:
            current = MouvementMateriel.objects.get(pk=self.pk)
            for field in ['description_bmm', 'emetteur_recepteur', 'departement_service']:
                if getattr(self, field) != getattr(current, field):
                    raise ValidationError(_('Un mouvement validé ne peut pas être modifié.'))
        
        # Si on tente de passer en VALIDE
        if self.statut == self.STATUT_VALIDE and self._original_statut == self.STATUT_BROUILLON:
            errors = {}
            
            # Vérifier les champs obligatoires
            required_fields = {
                'emetteur_recepteur': _('L\'émetteur/récepteur'),
                'departement_service': _('Le département/service'),
                'type_mouvement': _('Le type de mouvement'),
            }
            
            for field, label in required_fields.items():
                if not getattr(self, field):
                    errors[field] = _(f'{label} est obligatoire')
            
            # Vérifier qu'il y a au moins une ligne de mouvement
            if self.pk and not self.lignemouvement_set.exists():
                errors['__all__'] = _('Impossible de valider un mouvement sans articles')
            
            # Vérifier les lignes de mouvement
            if self.pk:
                ligne_errors = []
                for ligne in self.lignemouvement_set.all():
                    try:
                        ligne.clean()
                    except ValidationError as e:
                        ligne_errors.extend(e.messages)
                
                if ligne_errors:
                    if '__all__' not in errors:
                        errors['__all__'] = []
                    errors['__all__'].extend(ligne_errors)
            
            if errors:
                self.statut = self.STATUT_BROUILLON
                raise ValidationError(errors)

    def save(self, *args, **kwargs):
        print(f"Saving BMM {self.numero_bmm if self.numero_bmm else 'New'}")
        print(f"Current status: {self.statut}")
        print(f"Original status: {self._original_statut}")
        
        # Forcer BROUILLON pour les nouveaux BMM
        if not self.pk:
            self.statut = self.STATUT_BROUILLON
            
        # Générer le numéro BMM si nécessaire
        if not self.numero_bmm:
            self.generate_numero_bmm()
        
        # Détecter si on passe de BROUILLON à VALIDE
        is_validating = (
            self.statut == self.STATUT_VALIDE and 
            self._original_statut == self.STATUT_BROUILLON
        )
        
        print(f"Is validating: {is_validating}")
        
        # Sauvegarder dans une transaction
        with transaction.atomic():
            try:
                super().save(*args, **kwargs)
                
                if is_validating:
                    # Attendre que toutes les modifications soient appliquées
                    self.refresh_from_db()
                    for ligne in self.lignemouvement_set.all():
                        ligne.refresh_from_db()
                    
                    print("Calling update_stocks() after refresh")
                    self.update_stocks()
                    
            except ValidationError as e:
                self.statut = self.STATUT_BROUILLON
                raise
            finally:
                # Mettre à jour le statut original après la sauvegarde
                self._original_statut = self.statut

    def generate_numero_bmm(self):
        """Génère et assigne le prochain numéro BMM disponible"""
        last_bmm = MouvementMateriel.objects.order_by('-numero_bmm').first()
        if last_bmm:
            try:
                last_num = int(last_bmm.numero_bmm.replace('BMM', ''))
                self.numero_bmm = f'BMM{last_num + 1}'
            except (ValueError, AttributeError):
                self.numero_bmm = 'BMM1'
        else:
            self.numero_bmm = 'BMM1'

    def nombre_articles(self) -> int:
        try:
            return self.lignemouvement_set.count()
        except (AttributeError, TypeError):
            return 0

    def __str__(self) -> str:
        try:
            return f"{self.numero_bmm} - {self.get_type_mouvement_display()}"
        except AttributeError:
            return str(self.date_creation)

    class Meta:
        verbose_name = _('Mouvement de matériel')
        verbose_name_plural = _('Mouvements de matériel')
        ordering = ['-date_creation']

class LigneMouvement(models.Model):
    """Model representing a movement line."""
    mouvement = models.ForeignKey(
        MouvementMateriel,
        on_delete=models.CASCADE,
        verbose_name=_('Mouvement')
    )
    article = models.ForeignKey(
        'Article',
        on_delete=models.PROTECT,
        verbose_name=_('Article')
    )
    quantite = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        verbose_name=_('Quantité')
    )
    stock_avant = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Stock avant')
    )
    stock_apres = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Stock après')
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_quantite = self.quantite if self.pk else None
        
    def save(self, *args, **kwargs):
        print(f"Saving LigneMouvement - Quantité: {self.quantite}")
        print(f"Original quantité: {self._original_quantite}")
        
        # Si on met à jour uniquement certains champs, on ne recalcule pas les stocks
        update_fields = kwargs.get('update_fields')
        if update_fields and all(field in ['stock_avant', 'stock_apres'] for field in update_fields):
            return super().save(*args, **kwargs)
        
        # Mettre à jour stock_avant et stock_apres à chaque sauvegarde
        if self.article_id:
            # Si c'est une nouvelle ligne ou si la quantité a changé, recalculer
            if not self.pk or self.quantite != self._original_quantite:
                print(f"Initializing/Updating stocks - Original quantité: {self._original_quantite}, New quantité: {self.quantite}")
                
                # Récupérer l'article avec select_for_update
                with transaction.atomic():
                    article = Article.objects.select_for_update().get(pk=self.article_id)
                    
                    # Si c'est une modification d'un BMM validé
                    if self.pk and self.mouvement.statut == 'VALIDE':
                        # Annuler l'ancien mouvement
                        if self.mouvement.type_mouvement in [MouvementMateriel.TYPE_SORTIE_DEFINITIVE, MouvementMateriel.TYPE_SORTIE_PRET]:
                            article.quantite_stock += self._original_quantite
                        else:  # TYPE_ENTREE
                            article.quantite_stock -= self._original_quantite
                        article.save()
                        
                        # Rafraîchir le stock actuel
                        article.refresh_from_db()
                    
                    # Récupérer le stock actuel pour l'historique
                    self.stock_avant = article.quantite_stock
                    
                    # Calculer et appliquer le nouveau stock
                    if self.mouvement.type_mouvement in [MouvementMateriel.TYPE_SORTIE_DEFINITIVE, MouvementMateriel.TYPE_SORTIE_PRET]:
                        self.stock_apres = self.stock_avant - self.quantite
                        if self.mouvement.statut == 'VALIDE':
                            article.quantite_stock -= self.quantite
                    else:  # TYPE_ENTREE
                        self.stock_apres = self.stock_avant + self.quantite
                        if self.mouvement.statut == 'VALIDE':
                            article.quantite_stock += self.quantite
                    
                    print(f"Calculated - Stock avant: {self.stock_avant}, Stock après: {self.stock_apres}")
                    
                    # Sauvegarder le nouveau stock
                    if self.mouvement.statut == 'VALIDE':
                        article.save()
        
        # Sauvegarder
        super().save(*args, **kwargs)
        
        # Mettre à jour la quantité originale après la sauvegarde
        self._original_quantite = self.quantite

    def clean(self):
        """Validation de la ligne de mouvement"""
        super().clean()

        if not self.article_id:
            raise ValidationError(_('L\'article est obligatoire.'))

        if not self.quantite or self.quantite <= 0:
            raise ValidationError(_('La quantité doit être supérieure à 0.'))

        # Récupérer l'article directement depuis la base de données
        try:
            article = Article.objects.get(pk=self.article_id)
            if article.quantite_stock is None:
                raise ValidationError(_('L\'article n\'a pas de quantité en stock définie.'))
            
            # Vérifier qu'il y a assez de stock pour les sorties
            if self.mouvement.type_mouvement in [MouvementMateriel.TYPE_SORTIE_DEFINITIVE, MouvementMateriel.TYPE_SORTIE_PRET]:
                if article.quantite_stock < self.quantite:
                    raise ValidationError(
                        _('Stock insuffisant. Stock disponible : %(stock)s'),
                        params={'stock': article.quantite_stock}
                    )
        except Article.DoesNotExist:
            raise ValidationError(_('L\'article spécifié n\'existe pas.'))

    def __str__(self) -> str:
        return f"{self.article.code_article} - {self.quantite} {self.article.unite_mesure}"

    class Meta:
        verbose_name = _('Ligne de mouvement')
        verbose_name_plural = _('Lignes de mouvement')
        unique_together = ['mouvement', 'article']

def document_upload_path(instance: 'Document', filename: str) -> str:
    if instance.article:
        return f'documents/articles/{filename}'
    elif instance.equipement:
        return f'documents/equipements/{filename}'
    return f'documents/{filename}'

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from typing import Optional, Any, cast
from django.db import models
from django.core.exceptions import ValidationError

User = get_user_model()

class Document(models.Model):
    """Model representing a document."""
    fichier = models.FileField(
        verbose_name='Fichier',
        upload_to=document_upload_path  # type: ignore
    )
    remarque = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Remarque'
    )
    article = models.ForeignKey(
        'Article',
        on_delete=models.CASCADE,
        related_name='documents',
        null=True,
        blank=True
    )
    equipement = models.ForeignKey(
        'Equipement',
        on_delete=models.CASCADE,
        related_name='documents',
        null=True,
        blank=True
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='documents_uploades'
    )
    date_upload = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        verbose_name = _('Document')
        verbose_name_plural = _('Documents')

    def __str__(self) -> str:
        filename = self.fichier.name.split('/')[-1]  # Get only the filename without path
        if self.article:
            return f"{filename} - {self.article.code_article}"
        elif self.equipement:
            return f"{filename} - {self.equipement.tag}"
        return filename

    def clean(self) -> None:
        if not self.article and not self.equipement:
            raise ValidationError(_('Un document doit être associé soit à un article, soit à un équipement.'))
        if self.article and self.equipement:
            raise ValidationError(_('Un document ne peut pas être associé à la fois à un article et à un équipement.'))

    @property
    def user(self) -> Optional[AbstractUser]:
        if hasattr(self, 'uploaded_by') and self.uploaded_by is not None:
            return cast(AbstractUser, self.uploaded_by)
        return None

    def set_uploaded_by(self, user: AbstractUser) -> None:
        """Set the uploaded_by field with type safety."""
        self.uploaded_by = user

    def delete(self, *args, **kwargs):
        if self.fichier:
            storage = self.fichier.storage
            file_path = self.fichier.path
            
            # Delete the model instance
            super().delete(*args, **kwargs)
            
            # Delete the file after the model instance is deleted
            if storage.exists(file_path):
                storage.delete(file_path)
        else:
            super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        if self.pk:  # If this is an update
            try:
                old_instance = Document.objects.get(pk=self.pk)
                if old_instance.fichier and old_instance.fichier != self.fichier:  # If the file has changed
                    # Delete the old file
                    storage = old_instance.fichier.storage
                    file_path = old_instance.fichier.path
                    if storage.exists(file_path):
                        storage.delete(file_path)
            except Document.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)

class Platinage(DjangoModel):
    """Model representing a plating."""
    equipement = models.ForeignKey(
        Equipement,
        on_delete=models.CASCADE,
        related_name='platinages'
    )
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name='platinages'
    )
    type_platinage = models.ForeignKey(
        TypePlatinage,
        on_delete=models.CASCADE,
        related_name='platinages'
    )
    repere = models.CharField(
        max_length=100,
        null=False,
        blank=False,
        verbose_name=_('Repère')
    )
    date_debut = models.DateTimeField(null=True, blank=True)
    date_fin = models.DateTimeField(null=True, blank=True)
    remarque = models.TextField(blank=True, null=True)

    def __str__(self) -> str:
        return f"{self.repere} - {self.type_platinage.nom} - {self.article.code_article}"

    def clean(self) -> None:
        super().clean()
        if self.date_debut and self.date_fin and self.date_fin <= self.date_debut:
            raise ValidationError(_('La date de fin doit être postérieure à la date de début.'))

    class Meta(DjangoModel.Meta):
        verbose_name = _('Platinage')
        verbose_name_plural = _('Platinages')

class HistoriqueMouvement(DjangoModel):
    """Model representing a movement history."""
    TYPE_ACTION_CHOICES = [
        ('CREATION', 'Création'),
        ('VALIDATION', 'Validation'),
        ('ANNULATION', 'Annulation'),
    ]

    mouvement = models.ForeignKey(
        MouvementMateriel,
        on_delete=models.CASCADE,
        related_name='historiques'
    )
    type_action = models.CharField(
        max_length=20,
        choices=TYPE_ACTION_CHOICES
    )
    utilisateur = models.ForeignKey(
        UserModel,
        on_delete=models.CASCADE,
        related_name='historiques_mouvement'
    )
    date_action = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True, null=True)

    def __str__(self) -> str:
        if not (self.mouvement and hasattr(self, 'get_type_action_display')):
            return "Invalid history"
        mouvement_obj = cast(Any, self.mouvement)
        return f"{mouvement_obj.numero_bmm} - {cast(Any, self).get_type_action_display()}"

    class Meta(DjangoModel.Meta):
        ordering = ['-date_action']
        verbose_name = _('Historique de mouvement')
        verbose_name_plural = _('Historiques de mouvement')
