from django.db import models
from django.conf import settings
from documents.models import Document


class CorrectionIA(models.Model):

    class Statut(models.TextChoices):
        EN_ATTENTE = "EN_ATTENTE", "En attente"
        EN_COURS = "EN_COURS", "En cours"
        TERMINEE = "TERMINEE", "Terminée"
        ERREUR = "ERREUR", "Erreur"

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="corrections_ia"
    )

    effectuee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="corrections_ia"
    )

    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.EN_ATTENTE
    )

    resultat = models.TextField(blank=True)

    date_creation = models.DateTimeField(auto_now_add=True)

    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Correction IA - {self.document.titre}"