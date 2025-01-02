from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib import messages
from django.db import transaction
from django.db.models import Model, QuerySet, Count
from typing import TypeVar, Optional, Any, Sequence, Union
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.db.models.fields.related_descriptors import ManyToManyDescriptor
from django.contrib.auth import get_user_model
from django.contrib.admin import ModelAdmin
from django.forms import ModelForm
from django.forms.models import BaseInlineFormSet
from .models import (
    Site, Train, Unite, Equipement, Stock, Article,
    Phase, TypePlatinage, MouvementMateriel, Document,
    Platinage, HistoriqueMouvement, LigneMouvement,
    CategorieArticle, UniteMesure
)
from .forms import (
    MouvementMaterielForm, DocumentForm, ArticleForm,
    LigneMouvementForm, LigneMouvementInlineFormSet
)

T = TypeVar('T', bound=Model)

User = get_user_model()

class AuthenticatedHttpRequest(HttpRequest):
    user: User

class CustomModelAdmin(ModelAdmin):
    """Base class for all model admins in the application."""
    
    def save_model(self, request: AuthenticatedHttpRequest, obj: Any, form: ModelForm, change: bool) -> None:
        """Save the model and set the user if applicable."""
        if hasattr(obj, 'set_uploaded_by'):
            obj.set_uploaded_by(request.user)
        try:
            obj.save()
        except ValidationError as e:
            # Si une erreur de validation survient, forcer le statut en brouillon
            obj.statut = 'BROUILLON'
            messages.error(request, str(e))
            obj.save()

    def save_formset(self, request: AuthenticatedHttpRequest, form: ModelForm, formset: BaseInlineFormSet, change: bool) -> None:
        """Save formset instances and set the user if applicable."""
        instances: Sequence[Any] = formset.save(commit=False)
        for obj in instances:
            if hasattr(obj, 'set_uploaded_by'):
                obj.set_uploaded_by(request.user)
            try:
                obj.save()
            except ValidationError as e:
                messages.error(request, str(e))
                if hasattr(obj, 'mouvement'):
                    obj.mouvement.statut = 'BROUILLON'
                    obj.mouvement.save()
        formset.save_m2m()

    def response_add(self, request: AuthenticatedHttpRequest, obj: Any, post_url_continue: Optional[str] = None) -> Union[HttpResponseRedirect, TemplateResponse]:
        """Return response after adding an object."""
        return super().response_add(request, obj, post_url_continue)

    def response_change(self, request: AuthenticatedHttpRequest, obj: Any) -> Union[HttpResponseRedirect, TemplateResponse]:
        """Return response after changing an object."""
        return super().response_change(request, obj)

    def delete_view(self, request: AuthenticatedHttpRequest, object_id: str, extra_context: Optional[dict[str, Any]] = None) -> Union[TemplateResponse, HttpResponseRedirect]:
        """Return response for delete view."""
        return super().delete_view(request, object_id, extra_context)

class LigneMouvementInline(admin.TabularInline):
    model = LigneMouvement
    form = LigneMouvementForm
    formset = LigneMouvementInlineFormSet
    extra = 0
    min_num = 0
    validate_min = False
    autocomplete_fields = ['article']

    def get_fields(self, request, obj=None):
        """Retourne les champs à afficher selon le statut du mouvement parent."""
        fields = ['article', 'quantite']
        if obj and obj.statut == 'VALIDE' and not obj.is_being_validated:
            fields.extend(['stock_avant', 'stock_apres'])
        return fields

    def get_readonly_fields(self, request, obj=None):
        """Ne rendre les champs en lecture seule que si le mouvement parent est réellement validé."""
        if obj and obj.statut == 'VALIDE' and not obj.is_being_validated:
            return ['article', 'quantite', 'stock_avant', 'stock_apres']
        return []

    def has_delete_permission(self, request, obj=None):
        """Empêcher la suppression des lignes si le mouvement est validé."""
        if obj and obj.statut == 'VALIDE' and not obj.is_being_validated:
            return False
        return True

    def has_add_permission(self, request, obj=None):
        """Empêcher l'ajout de lignes si le mouvement est validé."""
        if obj and obj.statut == 'VALIDE' and not obj.is_being_validated:
            return False
        return True

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "article":
            kwargs["queryset"] = Article.objects.select_related('categorie_article', 'stock')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('article', 'article__categorie_article', 'article__stock')

@admin.register(MouvementMateriel)
class MouvementMaterielAdmin(CustomModelAdmin):
    form = MouvementMaterielForm
    inlines = [LigneMouvementInline]
    list_display = ('numero_bmm', 'type_mouvement', 'description_bmm', 'emetteur_recepteur', 
                   'departement_service', 'get_equipement_link', 'get_nombre_articles_link', 'remarque', 'get_colored_status', 
                   'created_by', 'date_creation', 'validated_by', 'date_validation')
    list_filter = ('type_mouvement', 'statut', 'created_by', 'validated_by')
    search_fields = ('numero_bmm', 'description_bmm', 'emetteur_recepteur', 'departement_service')
    readonly_fields = ('numero_bmm', 'created_by', 'date_creation', 'validated_by', 'date_validation')
    autocomplete_fields = ['equipement']
    actions = ['valider_mouvements', 'annuler_mouvements']

    class Media:
        css = {
            'all': ('admin/css/custom.css',)
        }

    @admin.action(description=_('Valider les mouvements sélectionnés'))
    def valider_mouvements(self, request: AuthenticatedHttpRequest, queryset: QuerySet[MouvementMateriel]) -> None:
        """Action pour valider plusieurs mouvements en même temps."""
        success_count = 0
        error_count = 0

        with transaction.atomic():
            for mouvement in queryset:
                try:
                    # On ne peut valider que les BMM en brouillon
                    if mouvement.statut == MouvementMateriel.STATUT_BROUILLON:
                        mouvement.statut = MouvementMateriel.STATUT_VALIDE
                        mouvement.validated_by = request.user
                        mouvement.date_validation = timezone.now()
                        mouvement.save()
                        mouvement.update_stocks()
                        
                        # Créer un historique
                        HistoriqueMouvement.objects.create(
                            mouvement=mouvement,
                            type_action='VALIDATION',
                            utilisateur=request.user,
                            details=f'Validation en lot du mouvement {mouvement.numero_bmm}'
                        )
                        
                        success_count += 1
                    else:
                        error_count += 1
                        messages.error(
                            request,
                            _(f'Le BMM {mouvement.numero_bmm} ne peut pas être validé car il n\'est pas en brouillon.')
                        )
                except Exception as e:
                    error_count += 1
                    messages.error(
                        request,
                        _(f'Erreur lors de la validation du BMM {mouvement.numero_bmm}: {str(e)}')
                    )

        if success_count > 0:
            messages.success(
                request,
                _(f'{success_count} mouvement(s) ont été validés avec succès.')
            )
        if error_count > 0:
            messages.warning(
                request,
                _(f'{error_count} mouvement(s) n\'ont pas pu être validés.')
            )

    @admin.display(description='Équipement')
    def get_equipement_link(self, obj):
        if obj.equipement:
            return format_html('<div class="wide-column"><a href="{}">{}</a></div>',
                             reverse('admin:gestion_prep_equipement_change', args=[obj.equipement.pk]),
                             obj.equipement)
        return '-'

    def get_nombre_articles_link(self, obj):
        count = obj.lignemouvement_set.count()
        url = f"/admin/gestion_prep/lignemouvement/?mouvement__id__exact={obj.id}"
        return format_html('<a href="{}">{} article(s)</a>', url, count)
    get_nombre_articles_link.short_description = "Nombre d'articles"
    get_nombre_articles_link.admin_order_field = 'lignemouvement__count'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            lignemouvement__count=Count('lignemouvement')
        )
        return queryset

    @admin.display(description="Statut")
    def get_colored_status(self, obj):
        status_colors = {
            'BROUILLON': 'orange',
            'VALIDE': 'green',
            'ANNULE': 'red'
        }
        color = status_colors.get(obj.statut, 'black')
        url = reverse('admin:gestion_prep_lignemouvement_changelist') + f'?mouvement__id={obj.id}'
        return format_html(
            '<a href="{}" style="color: {};">{}</a>',
            url, color, obj.get_statut_display()
        )
    get_colored_status.short_description = "Statut"
    get_colored_status.admin_order_field = 'statut'

    def annuler_mouvements(self, request: AuthenticatedHttpRequest, queryset: QuerySet[MouvementMateriel]) -> None:
        """Action pour annuler plusieurs mouvements en même temps."""
        success_count = 0
        error_count = 0
        
        for mouvement in queryset:
            try:
                # On ne peut annuler que les BMM en brouillon
                if mouvement.statut == MouvementMateriel.STATUT_BROUILLON:
                    mouvement.statut = MouvementMateriel.STATUT_ANNULE
                    mouvement.save()
                    success_count += 1
                else:
                    error_count += 1
                    messages.error(
                        request,
                        _(f'Le BMM {mouvement.numero_bmm} ne peut pas être annulé car il n\'est pas en brouillon.')
                    )
            except Exception as e:
                error_count += 1
                messages.error(
                    request,
                    _(f'Erreur lors de l\'annulation du BMM {mouvement.numero_bmm}: {str(e)}')
                )
        
        if success_count > 0:
            messages.success(
                request,
                _(f'{success_count} mouvement(s) ont été annulés avec succès.')
            )
        if error_count > 0:
            messages.warning(
                request,
                _(f'{error_count} mouvement(s) n\'ont pas pu être annulés.')
            )
    
    annuler_mouvements.short_description = _("Annuler les mouvements sélectionnés")

    def has_change_permission(self, request, obj=None):
        """Empêcher la modification des BMM annulés."""
        if obj and obj.statut == MouvementMateriel.STATUT_ANNULE:
            return False
        return super().has_change_permission(request, obj)

    def get_actions(self, request: AuthenticatedHttpRequest) -> dict[str, Any]:
        """Ne montrer l'action de validation qu'aux utilisateurs ayant la permission."""
        actions = super().get_actions(request)
        if not request.user.has_perm('gestion_prep.validate_mouvementmateriel'):
            if 'valider_mouvements' in actions:
                del actions['valider_mouvements']
        return actions

    def save_model(self, request: AuthenticatedHttpRequest, obj: MouvementMateriel, form: MouvementMaterielForm, change: bool) -> None:
        """Sauvegarde du mouvement avec validation."""
        try:
            # Si c'est une nouvelle création
            if not change:
                obj.created_by = request.user
                obj.date_creation = timezone.now()
                obj.save()
                return

            # Si on tente de valider
            if obj.is_being_validated:
                try:
                    # Validation complète
                    obj.clean()
                    form.clean()
                    
                    # Si la validation passe, mettre à jour les infos
                    obj.validated_by = request.user
                    obj.date_validation = timezone.now()
                    
                    # Mise à jour des stocks
                    with transaction.atomic():
                        obj.save()
                        obj.update_stocks()
                        
                        # Créer un historique
                        HistoriqueMouvement.objects.create(
                            mouvement=obj,
                            type_action='VALIDATION',
                            utilisateur=request.user,
                            details=f'Validation du mouvement {obj.numero_bmm}'
                        )
                    
                    messages.success(request, _(f'Le mouvement {obj.numero_bmm} a été validé avec succès.'))
                
                except ValidationError as e:
                    # En cas d'erreur, afficher les messages
                    if hasattr(e, 'message_dict'):
                        for field, errors in e.message_dict.items():
                            if isinstance(errors, list):
                                for error in errors:
                                    messages.error(request, f"{field}: {error}")
                            else:
                                messages.error(request, f"{field}: {errors}")
                    else:
                        messages.error(request, str(e))
                    
                    # Sauvegarder avec le statut BROUILLON
                    obj.set_validation_error(True)
                    obj.save()
                    return
            else:
                # Pour les autres modifications
                obj.save()
        
        except Exception as e:
            messages.error(request, str(e))
            if obj.pk:
                obj.refresh_from_db()

    def response_change(self, request: AuthenticatedHttpRequest, obj: MouvementMateriel) -> HttpResponseRedirect:
        """Personnalisation de la réponse après modification."""
        response = super().response_change(request, obj)
        
        # Si des erreurs sont présentes, rediriger vers le formulaire
        if messages.get_messages(request):
            return HttpResponseRedirect(request.path)
            
        return response

    def get_readonly_fields(self, request: AuthenticatedHttpRequest, obj: Optional[MouvementMateriel] = None) -> tuple[str, ...]:
        """Définit les champs en lecture seule selon le statut."""
        readonly = ['numero_bmm', 'created_by', 'date_creation', 'validated_by', 'date_validation']
        
        if obj and obj.statut == 'VALIDE' and not obj.is_being_validated:
            readonly.extend([
                'type_mouvement', 'description_bmm', 'emetteur_recepteur',
                'departement_service', 'date_retour_prevue', 'date_retour_effective',
                'equipement', 'remarque', 'statut'
            ])
        
        return readonly

@admin.register(LigneMouvement)
class LigneMouvementAdmin(CustomModelAdmin):
    form = LigneMouvementForm
    list_display = ('mouvement', 'article', 'quantite', 'get_bmm_status')
    list_filter = ('mouvement__statut', 'mouvement__type_mouvement')
    search_fields = ('article__designation', 'mouvement__numero_bmm')
    autocomplete_fields = ['article', 'mouvement']

    def get_bmm_status(self, obj):
        url = f"/admin/gestion_prep/mouvementmateriel/{obj.mouvement.id}/change/"
        status_colors = {
            'BROUILLON': 'orange',
            'VALIDE': 'green',
            'ANNULE': 'red'
        }
        color = status_colors.get(obj.mouvement.statut, 'black')
        return format_html('<a href="{}" style="color: {};">{}</a>', 
                         url, color, obj.mouvement.statut)
    get_bmm_status.short_description = "Statut BMM"
    get_bmm_status.admin_order_field = 'mouvement__statut'

    def get_list_display(self, request):
        list_display = ['mouvement', 'article', 'quantite', 'get_bmm_status']
        if 'mouvement__statut__exact=VALIDE' in request.GET.get('_changelist_filters', ''):
            list_display.extend(['stock_avant', 'stock_apres'])
        return list_display

    def get_fields(self, request, obj=None):
        fields = ['mouvement', 'article', 'quantite']
        if obj and obj.mouvement.statut == 'VALIDE':
            fields.extend(['stock_avant', 'stock_apres'])
        return fields

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.mouvement.statut == 'VALIDE':
            return ['mouvement', 'article', 'quantite', 'stock_avant', 'stock_apres']
        return []

    @admin.display(description=_('Stock après opération'))
    def stock_apres(self, obj):
        stock = obj.stock_apres
        return str(stock) if stock is not None else '-'

    def save_model(self, request, obj, form, change):
        if not change:  # Nouvelle ligne
            obj.stock_avant = obj.article.quantite_stock
        super().save_model(request, obj, form, change)

class DocumentInline(admin.TabularInline):
    model = Document
    extra = 1
    fields = ['fichier', 'remarque']

    def get_queryset(self, request: AuthenticatedHttpRequest) -> "QuerySet[Any]":
        return super().get_queryset(request).filter(article__isnull=False)

    def save_model(self, request: AuthenticatedHttpRequest, obj: Any, form: ModelForm, change: bool) -> None:
        if not change and isinstance(obj, Document):
            obj.set_uploaded_by(request.user)
            try:
                obj.save()
            except ValidationError as e:
                messages.error(request, str(e))

    def save_formset(self, request: AuthenticatedHttpRequest, form: ModelForm, formset: BaseInlineFormSet, change: bool) -> None:
        instances: Sequence[Any] = formset.save(commit=False)
        
        # Gérer les suppressions en premier
        for obj in formset.deleted_objects:
            if isinstance(obj, Document):
                obj.delete()  # Ceci appellera notre méthode delete personnalisée
        
        # Sauvegarder les nouvelles instances et les modifications
        for instance in instances:
            if isinstance(instance, Document):
                # Toujours définir l'utilisateur, que ce soit une création ou une modification
                instance.set_uploaded_by(request.user)
                try:
                    instance.save()
                except ValidationError as e:
                    messages.error(request, str(e))

        formset.save_m2m()

@admin.register(Document)
class DocumentAdmin(CustomModelAdmin):
    form = DocumentForm
    list_display = ('get_fichier_display', 'get_parent_display', 'remarque', 'uploaded_by', 'date_upload')
    list_filter = ('date_upload', 'uploaded_by')
    search_fields = ('fichier', 'remarque', 'article__code_article', 'equipement__tag')
    autocomplete_fields = ['article', 'equipement', 'uploaded_by']

    @admin.display(description='Fichier')
    def get_fichier_display(self, obj):
        if obj.fichier:
            try:
                if obj.fichier.storage.exists(obj.fichier.name):
                    return format_html('<a href="{}">{}</a>', obj.fichier.url, obj.fichier.name)
                return f"{obj.fichier.name} (fichier manquant)"
            except Exception:
                return f"{obj.fichier.name} (erreur d'accès)"
        return "(sans fichier)"

    @admin.display(description='Parent')
    def get_parent_display(self, obj):
        if obj.equipement:
            return f"Équipement: {obj.equipement}"
        elif obj.article:
            return f"Article: {obj.article}"
        return "-"

@admin.register(Equipement)
class EquipementAdmin(CustomModelAdmin):
    list_display = ('tag', 'description', 'train', 'get_platinages_count', 'get_documents_count')
    list_filter = ('train__unite__site', 'train__unite', 'train', 'platinages__type_platinage')
    search_fields = ('tag', 'description')
    ordering = ['tag']
    autocomplete_fields = ['train']
    inlines = [DocumentInline]

    def save_formset(self, request: AuthenticatedHttpRequest, form, formset, change):
        instances = formset.save(commit=False)
        
        # Gérer les suppressions en premier
        for obj in formset.deleted_objects:
            if isinstance(obj, Document):
                obj.delete()  # Ceci appellera notre méthode delete personnalisée
        
        # Sauvegarder les nouvelles instances et les modifications
        for instance in instances:
            if isinstance(instance, Document):
                # Toujours définir l'utilisateur, que ce soit une création ou une modification
                instance.set_uploaded_by(request.user)
                try:
                    instance.save()
                except ValidationError as e:
                    messages.error(request, str(e))

        formset.save_m2m()

    def save_model(self, request: AuthenticatedHttpRequest, obj: Any, form: ModelForm, change: bool) -> None:
        if not change:
            obj.save()
        super().save_model(request, obj, form, change)

    @admin.display(description='Nombre de platinages')
    def get_platinages_count(self, obj: Equipement) -> str:
        count = obj.platinages.count()
        if count == 0:
            return format_html('<span style="color: red;">0</span>')
        url = f"{reverse('admin:gestion_prep_platinage_changelist')}?equipement={obj.pk}"
        return format_html('<a href="{}">{}</a>', url, count)

    @admin.display(description='Documents')
    def get_documents_count(self, obj: Equipement) -> str:
        count = obj.documents.count()
        if count == 0:
            return format_html('<span style="color: red;">0</span>')
        url = f"{reverse('admin:gestion_prep_document_changelist')}?equipement={obj.pk}"
        return format_html('<a href="{}">{}</a>', url, count)

@admin.register(Train)
class TrainAdmin(CustomModelAdmin):
    list_display = ('nom', 'get_unite', 'get_site', 'description', 'get_equipements_count')
    list_filter = ('unite__site', 'unite')
    search_fields = ('nom', 'unite__nom', 'unite__site__nom')
    autocomplete_fields = ['unite']

    @admin.display(description='Unité', ordering='unite__nom')
    def get_unite(self, obj: Train) -> str:
        if not obj.unite:
            return ''
        unite_obj = obj.unite
        return str(unite_obj.nom)

    @admin.display(description='Site', ordering='unite__site__nom')
    def get_site(self, obj: Train) -> str:
        if not obj.unite or not getattr(obj.unite, 'site', None):
            return ''
        unite_obj = obj.unite
        site_obj = unite_obj.site
        return str(site_obj.nom)

    @admin.display(description='Nombre d\'équipements')
    def get_equipements_count(self, obj: Train) -> str:
        count = Equipement.objects.filter(train=obj).count()
        if count == 0:
            return format_html('<span style="color: red;">0</span>')
        url = f"{reverse('admin:gestion_prep_equipement_changelist')}?train__id__exact={obj.pk}"
        return format_html('<a href="{}">{}</a>', url, count)

@admin.register(Unite)
class UniteAdmin(CustomModelAdmin):
    list_display = ('nom', 'get_site', 'description', 'get_trains_count')
    list_filter = ('site',)
    search_fields = ('nom', 'site__nom')
    autocomplete_fields = ['site']

    @admin.display(description='Site', ordering='site__nom')
    def get_site(self, obj: Unite) -> str:
        if not obj.site:
            return ''
        site_obj = obj.site
        return str(site_obj.nom)

    @admin.display(description='Nombre de trains')
    def get_trains_count(self, obj: Unite) -> str:
        count = Train.objects.filter(unite=obj).count()
        if count == 0:
            return format_html('<span style="color: red;">0</span>')
        url = f"{reverse('admin:gestion_prep_train_changelist')}?unite__id__exact={obj.pk}"
        return format_html('<a href="{}">{}</a>', url, count)

from django.db.models.fields.related_descriptors import ManyToManyDescriptor
from django.db.models import QuerySet

@admin.register(Phase)
class PhaseAdmin(CustomModelAdmin):
    list_display = ('nom', 'description', 'get_platinages_count')
    list_filter = ('nom', 'platinages__type_platinage')
    search_fields = ('nom', 'description')
    ordering = ['nom']
    filter_horizontal = ('platinages',)

    @admin.display(description='Nombre de platinages')
    def get_platinages_count(self, obj: Phase) -> str:
        count = Platinage.objects.filter(phases=obj).count()
        if count == 0:
            return format_html('<span style="color: red;">0</span>')
        url = f"{reverse('admin:gestion_prep_platinage_changelist')}?phases__id__exact={obj.pk}"
        return format_html('<a href="{}">{}</a>', url, count)

@admin.register(Stock)
class StockAdmin(CustomModelAdmin):
    list_display = ('nom', 'site', 'type_stock', 'emplacement', 'get_articles_count')
    list_filter = ('site', 'type_stock')
    search_fields = ('nom', 'description', 'emplacement')
    autocomplete_fields = ['site']

    @admin.display(description='Nombre d\'articles')
    def get_articles_count(self, obj: Stock) -> str:
        count = Article.objects.filter(stock=obj).count()
        if count == 0:
            return format_html('<span style="color: red;">0</span>')
        url = f"{reverse('admin:gestion_prep_article_changelist')}?stock__id__exact={obj.pk}"
        return format_html('<a href="{}">{}</a>', url, count)

@admin.register(TypePlatinage)
class TypePlatinageAdmin(CustomModelAdmin):
    list_display = ('nom', 'description', 'get_articles_count', 'get_equipements_count', 'get_phases_count')
    list_filter = ('nom',)
    search_fields = ('nom', 'description')
    ordering = ['nom']

    @admin.display(description='Nombre d\'articles')
    def get_articles_count(self, obj: TypePlatinage) -> str:
        count = Article.objects.filter(platinages__type_platinage=obj).distinct().count()
        if count == 0:
            return format_html('<span style="color: red;">0</span>')
        url = f"{reverse('admin:gestion_prep_article_changelist')}?platinages__type_platinage={obj.pk}"
        return format_html('<a href="{}">{}</a>', url, count)

    @admin.display(description='Nombre d\'équipements')
    def get_equipements_count(self, obj: TypePlatinage) -> str:
        count = Equipement.objects.filter(platinages__type_platinage=obj).distinct().count()
        if count == 0:
            return format_html('<span style="color: red;">0</span>')
        url = f"{reverse('admin:gestion_prep_equipement_changelist')}?platinages__type_platinage={obj.pk}"
        return format_html('<a href="{}">{}</a>', url, count)

    @admin.display(description='Nombre de phases')
    def get_phases_count(self, obj: TypePlatinage) -> str:
        count = Phase.objects.filter(platinages__type_platinage=obj).distinct().count()
        if count == 0:
            return format_html('<span style="color: red;">0</span>')
        url = f"{reverse('admin:gestion_prep_phase_changelist')}?platinages__type_platinage={obj.pk}"
        return format_html('<a href="{}">{}</a>', url, count)

@admin.register(Platinage)
class PlatinageAdmin(CustomModelAdmin):
    list_display = ('equipement', 'article', 'type_platinage', 'repere', 'get_phases', 'date_debut', 'date_fin')
    list_filter = ('equipement__train__unite__site', 'equipement__train__unite', 'equipement__train', 'phases', 'type_platinage')
    search_fields = ('equipement__tag', 'article__code_article', 'repere')
    ordering = ['equipement__tag', 'article__code_article']
    autocomplete_fields = ['equipement', 'article', 'type_platinage']
    date_hierarchy = 'date_debut'

    @admin.display(description='Phases')
    def get_phases(self, obj: Platinage) -> str:
        phases = Phase.objects.filter(platinages=obj)
        return ", ".join(phase.nom for phase in phases)

    @admin.display(description='Équipement', ordering='equipement__tag')
    def get_equipement(self, obj: Platinage) -> str:
        if not obj.equipement:
            return ''
        equipement_obj = obj.equipement
        return str(equipement_obj.tag)

    @admin.display(description='Article', ordering='article__code_article')
    def get_article(self, obj: Platinage) -> str:
        if not obj.article:
            return ''
        article_obj = obj.article
        return str(article_obj.code_article)

@admin.register(HistoriqueMouvement)
class HistoriqueMouvementAdmin(admin.ModelAdmin):
    list_display = ('mouvement', 'type_action', 'utilisateur', 'date_action')
    list_filter = ('type_action', 'utilisateur')
    search_fields = ('mouvement__numero_bmm', 'details')
    date_hierarchy = 'date_action'
    autocomplete_fields = ['mouvement', 'utilisateur']

@admin.register(CategorieArticle)
class CategorieArticleAdmin(CustomModelAdmin):
    list_display = ('nom', 'description', 'get_articles_count')
    list_filter = ('nom',)
    search_fields = ('nom', 'description')
    ordering = ['nom']

    @admin.display(description='Nombre d\'articles')
    def get_articles_count(self, obj: CategorieArticle) -> str:
        count = Article.objects.filter(categorie_article=obj).count()
        if count == 0:
            return format_html('<span style="color: red;">0</span>')
        url = f"{reverse('admin:gestion_prep_article_changelist')}?categorie_article__id__exact={obj.pk}"
        return format_html('<a href="{}">{}</a>', url, count)

@admin.register(Article)
class ArticleAdmin(CustomModelAdmin):
    form = ArticleForm
    list_display = ('code_article', 'description', 'stock', 'unite_mesure', 'quantite_stock', 'get_documents_count', 'get_mouvements_count', 'get_platinages_count')
    list_filter = (
        'stock__site',
        'stock',
        'categorie_article',
        'stock__type_stock',
        'platinages__type_platinage',
    )
    search_fields = ['code_article', 'description', 'specification']
    ordering = ['code_article']
    autocomplete_fields = ['stock', 'categorie_article', 'unite_mesure']
    inlines = [DocumentInline]

    def get_search_results(self, request: AuthenticatedHttpRequest, queryset, search_term):
        queryset = queryset.select_related('stock', 'categorie_article')
        return super().get_search_results(request, queryset, search_term)

    @admin.display(description='Documents')
    def get_documents_count(self, obj: Article) -> str:
        count = Document.objects.filter(article=obj).count()
        if count == 0:
            return format_html('<span style="color: red;">0</span>')
        url = f"{reverse('admin:gestion_prep_document_changelist')}?article__id__exact={obj.pk}"
        return format_html('<a href="{}">{}</a>', url, count)

    @admin.display(description='Mouvements')
    def get_mouvements_count(self, obj: Article) -> str:
        count = LigneMouvement.objects.filter(article=obj).count()
        if count == 0:
            return format_html('<span style="color: red;">0</span>')
        url = f"{reverse('admin:gestion_prep_lignemouvement_changelist')}?article__id__exact={obj.pk}"
        return format_html('<a href="{}">{}</a>', url, count)

    @admin.display(description='Platinages')
    def get_platinages_count(self, obj: Article) -> str:
        count = Platinage.objects.filter(article=obj).count()
        if count == 0:
            return format_html('<span style="color: red;">0</span>')
        url = f"{reverse('admin:gestion_prep_platinage_changelist')}?article__id__exact={obj.pk}"
        return format_html('<a href="{}">{}</a>', url, count)

    def save_formset(self, request: AuthenticatedHttpRequest, form, formset, change):
        instances = formset.save(commit=False)
        
        # Gérer les suppressions en premier
        for obj in formset.deleted_objects:
            if isinstance(obj, Document):
                obj.delete()  # Ceci appellera notre méthode delete personnalisée
        
        # Sauvegarder les nouvelles instances et les modifications
        for instance in instances:
            if isinstance(instance, Document):
                # Toujours définir l'utilisateur, que ce soit une création ou une modification
                instance.set_uploaded_by(request.user)
                try:
                    instance.save()
                except ValidationError as e:
                    messages.error(request, str(e))

        formset.save_m2m()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "unite_mesure":
            kwargs["queryset"] = UniteMesure.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Site)
class SiteAdmin(CustomModelAdmin):
    list_display = ('nom', 'description', 'get_unites_count')
    search_fields = ('nom', 'description')
    ordering = ['nom']

    @admin.display(description='Nombre d\'unités')
    def get_unites_count(self, obj: Site) -> str:
        count = Unite.objects.filter(site=obj).count()
        if count == 0:
            return format_html('<span style="color: red;">0</span>')
        url = f"{reverse('admin:gestion_prep_unite_changelist')}?site__id__exact={obj.pk}"
        return format_html('<a href="{}">{}</a>', url, count)

@admin.register(UniteMesure)
class UniteMesureAdmin(CustomModelAdmin):
    list_display = ('nom', 'symbole', 'description')
    search_fields = ('nom', 'symbole', 'description')
    ordering = ['nom']
    search_help_text = "Rechercher par nom ou symbole"

    def get_search_results(self, request: AuthenticatedHttpRequest, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        return queryset, use_distinct
