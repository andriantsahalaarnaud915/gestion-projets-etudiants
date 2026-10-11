from django.db import models
from django.conf import settings
from projets.models import Projet

class Document(models.Model):
    class TypeDocument(models.TextChoices):
        CAHIER = "CAHIER", "Cahier des charges"
        RAPPORT = "RAPPORT", "Rapport"
        PRESENTATION = "PRESENTATION", "Présentation"
        CODE = "CODE", "Code source"
        AUTRE = "AUTRE", "Autre"

    class Statut(models.TextChoices):
        DEPOSE = "DEPOSE", "Déposé"
        EN_COURS = "EN_COURS", "En cours de validation"
        VALIDE = "VALIDE", "Validé"
        REFUSE = "REFUSE", "Refusé"

    titre = models.CharField(max_length=255)
    fichier = models.FileField(upload_to="documents/%Y/%m/")
    type_document = models.CharField(
        max_length=20,
        choices=TypeDocument.choices,
        default=TypeDocument.AUTRE
    )
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.DEPOSE
    )
    projet = models.ForeignKey(
        Projet,
        on_delete=models.CASCADE,
        related_name="documents"
    )
    depose_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="documents_deposes"
    )
    date_depot = models.DateTimeField(auto_now_add=True)
    commentaire = models.TextField(blank=True)

    def __str__(self):
        return f"{self.titre} - {self.projet.titre}"