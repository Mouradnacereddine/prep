from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from typing import Dict, Any
from .models import (
    Article, Document, Equipement, LigneMouvement, MouvementMateriel
)

class MouvementMaterielForm(forms.ModelForm):
    class Meta:
        model = MouvementMateriel
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_data = None
        
        if self.instance and self.instance.pk:
            self.original_data = {
                'statut': self.instance.statut,
                'data': self.data.copy() if self.data else None
            }

    def clean(self):
        cleaned_data = super().clean()
        
        # Si on tente de valider
        if self.instance.is_being_validated:
            # Vérifier les champs obligatoires
            required_fields = {
                'emetteur_recepteur': _('L\'émetteur/récepteur'),
                'departement_service': _('Le département/service'),
                'type_mouvement': _('Le type de mouvement'),
            }
            
            errors = {}
            for field, label in required_fields.items():
                if not cleaned_data.get(field):
                    errors[field] = _(f'{label} est obligatoire')
            
            # Vérifier la date de retour pour les prêts
            if cleaned_data.get('type_mouvement') == 'SORTIE_PRET' and not cleaned_data.get('date_retour_prevue'):
                errors['date_retour_prevue'] = _('La date de retour prévue est obligatoire pour les sorties à titre de prêt')
            
            # S'il y a des erreurs, forcer le statut en BROUILLON
            if errors:
                cleaned_data['statut'] = 'BROUILLON'
                self.instance.set_validation_error(True)
                raise ValidationError(errors)
            
            # Vérifier les lignes de mouvement
            if self.instance and self.instance.pk:
                ligne_errors = []
                for ligne in self.instance.lignemouvement_set.all():
                    try:
                        ligne.clean()
                    except ValidationError as e:
                        ligne_errors.extend(e.messages)
                
                if ligne_errors:
                    cleaned_data['statut'] = 'BROUILLON'
                    self.instance.set_validation_error(True)
                    raise ValidationError({
                        'statut': [_('Le mouvement ne peut pas être validé car il y a des erreurs dans les lignes :')] + ligne_errors
                    })
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Si on a des erreurs de validation
        if instance.is_being_validated and self.errors:
            instance.set_validation_error(True)
            # Restaurer les données originales si disponibles
            if self.original_data and self.original_data['data']:
                self.data = self.original_data['data']
        
        if commit:
            instance.save()
        
        return instance

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = '__all__'

class LigneMouvementInlineFormSet(forms.BaseInlineFormSet):
    def clean(self):
        """Validation du formset complet"""
        if any(self.errors):
            return

        articles = []
        empty_lines = []
        has_empty_line = False
        article_counts = {}  # Pour suivre les articles en double
        
        for i, form in enumerate(self.forms):
            if form.cleaned_data.get('DELETE'):
                continue
                
            article = form.cleaned_data.get('article')
            quantite = form.cleaned_data.get('quantite')
            
            if not article and not quantite:
                # Ligne complètement vide
                empty_lines.append(i + 1)  # +1 pour avoir le numéro de ligne humain
                continue
                
            if not article or not quantite:
                has_empty_line = True
                empty_lines.append(i + 1)
            else:
                articles.append(article)
                # Vérifier les doublons
                if article.id in article_counts:
                    article_counts[article.id] += 1
                else:
                    article_counts[article.id] = 1

        # Vérifier s'il y a des articles en double
        duplicate_articles = [article_id for article_id, count in article_counts.items() if count > 1]
        if duplicate_articles:
            duplicate_names = [Article.objects.get(id=article_id).code_article for article_id in duplicate_articles]
            raise ValidationError(_('Les articles suivants sont présents plusieurs fois : %(articles)s. Chaque article ne peut être utilisé qu\'une seule fois par mouvement.') % {'articles': ', '.join(duplicate_names)})

        if not articles:
            raise ValidationError(_('Au moins une ligne avec un article est requise'))
            
        if has_empty_line or empty_lines:
            if len(empty_lines) == 1:
                raise ValidationError(_('La ligne %(line)s est incomplète. Veuillez sélectionner un article et spécifier une quantité.') % {'line': empty_lines[0]})
            else:
                raise ValidationError(_('Les lignes suivantes sont incomplètes : %(lines)s. Veuillez sélectionner un article et spécifier une quantité pour chaque ligne.') % {'lines': ', '.join(map(str, empty_lines))})
            
        if self.instance and self.instance.statut == 'VALIDE':
            for form in self.forms:
                if form.cleaned_data.get('DELETE', False):
                    raise ValidationError(_('Impossible de supprimer une ligne quand le BMM est validé'))

    def save(self, commit=True):
        """Ne sauvegarde que les lignes complètes"""
        instances = super().save(commit=False)
        saved_instances = []
        
        for instance in instances:
            if instance.article is not None and instance.quantite:
                if commit:
                    instance.save()
                saved_instances.append(instance)
                
        if commit:
            self.save_m2m()
            
        return saved_instances

class LigneMouvementForm(forms.ModelForm):
    class Meta:
        model = LigneMouvement
        fields = ['mouvement', 'article', 'quantite']
        error_messages = {
            'article': {
                'required': _('Vous devez sélectionner un article.'),
            },
            'mouvement': {
                'required': _('Vous devez sélectionner un mouvement.'),
            },
            'quantite': {
                'required': _('Vous devez spécifier une quantité.'),
                'invalid': _('La quantité doit être un nombre entier valide.'),
                'min_value': _('La quantité doit être strictement supérieure à 0.'),
            },
        }

    def clean(self):
        """Validation globale de la ligne de mouvement"""
        cleaned_data = super().clean()
        
        # Si le formulaire est marqué pour suppression, on ne fait pas de validation
        if self.cleaned_data.get('DELETE'):
            return cleaned_data
            
        article = cleaned_data.get('article')
        quantite = cleaned_data.get('quantite')
        
        # Vérifier que les deux champs sont remplis ensemble
        if bool(article) != bool(quantite):
            if not article:
                self.add_error('article', _('L\'article est obligatoire si une quantité est spécifiée'))
            if not quantite:
                self.add_error('quantite', _('La quantité est obligatoire si un article est spécifié'))
        
        return cleaned_data

    def clean_quantite(self):
        """Validation approfondie de la quantité"""
        quantite = self.cleaned_data.get('quantite')
        
        if self.cleaned_data.get('DELETE'):
            return quantite
            
        # Vérifier si la quantité est vide ou None
        if quantite is None or quantite == '':
            raise ValidationError(_('La quantité est obligatoire.'))
        
        # Convertir en entier
        try:
            quantite = int(quantite)
        except (TypeError, ValueError):
            raise ValidationError(_('La quantité doit être un nombre entier valide.'))
            
        # Vérifier que la quantité est positive
        if quantite <= 0:
            raise ValidationError(_('La quantité doit être strictement supérieure à 0.'))
            
        return quantite

class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = '__all__'
        widgets = {
            'code_article': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Entrez le code article'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Description détaillée de l\'article'}),
            'specification': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Spécifications techniques'}),
            'quantite_initiale': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'quantite_stock': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'seuil_alerte': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        quantite_initiale = cleaned_data.get('quantite_initiale')
        quantite_stock = cleaned_data.get('quantite_stock')
        seuil_alerte = cleaned_data.get('seuil_alerte')

        if quantite_initiale is not None and quantite_initiale < 0:
            raise ValidationError({'quantite_initiale': 'La quantité initiale ne peut pas être négative'})
        
        if quantite_stock is not None and quantite_stock < 0:
            raise ValidationError({'quantite_stock': 'La quantité en stock ne peut pas être négative'})
        
        if seuil_alerte is not None and seuil_alerte < 0:
            raise ValidationError({'seuil_alerte': 'Le seuil d\'alerte ne peut pas être négatif'})

        return cleaned_data

class EquipementForm(forms.ModelForm):
    class Meta:
        model = Equipement
        fields = '__all__'
