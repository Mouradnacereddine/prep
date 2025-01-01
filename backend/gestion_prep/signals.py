from django.db.models.signals import pre_delete, post_delete
from django.dispatch import receiver
from .models import Document, Article, Equipement
import os
from django.conf import settings

@receiver(pre_delete, sender=Document)
def delete_document_files(sender, instance, **kwargs):
    """Supprime le fichier physique associé au document avant la suppression de l'instance"""
    if instance.fichier:
        file_path = os.path.join(settings.MEDIA_ROOT, str(instance.fichier))
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Erreur lors de la suppression du fichier {file_path}: {str(e)}")

@receiver(pre_delete, sender=Article)
def delete_article_files(sender, instance, **kwargs):
    """Supprime tous les fichiers associés à l'article avant sa suppression"""
    for document in instance.documents.all():
        if document.fichier:
            file_path = os.path.join(settings.MEDIA_ROOT, str(document.fichier))
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Erreur lors de la suppression du fichier {file_path}: {str(e)}")

@receiver(pre_delete, sender=Equipement)
def delete_equipement_files(sender, instance, **kwargs):
    """Supprime tous les fichiers associés à l'équipement avant sa suppression"""
    for document in instance.documents.all():
        if document.fichier:
            file_path = os.path.join(settings.MEDIA_ROOT, str(document.fichier))
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Erreur lors de la suppression du fichier {file_path}: {str(e)}")