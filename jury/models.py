from django.db import models
from django.conf import settings
from projets.models import Projet


class Soutenance(models.Model):

    class Statut(models.TextChoices):
        PLANIFIEE = "PLANIFIEE", "Planifiée"
        EN_COURS = "EN_COURS", "En cours"
        TERMINEE = "TERMINEE", "Terminée"
        ANNULEE = "ANNULEE", "Annulée"

    projet = models.ForeignKey(
        Projet,
        on_delete=models.CASCADE,
        related_name="soutenances"
    )

    date = models.DateField()

    heure = models.TimeField()

    salle = models.CharField(
        max_length=150
    )

    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.PLANIFIEE
    )

    commentaire = models.TextField(
        blank=True
    )

    creee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="soutenances_creees"
    )

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    date_modification = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.projet.titre} - {self.date}"

    class Meta:
        ordering = ["date", "heure"]


class MembreJury(models.Model):

    class Fonction(models.TextChoices):
        PRESIDENT = "PRESIDENT", "Président"
        RAPPORTEUR = "RAPPORTEUR", "Rapporteur"
        EXAMINATEUR = "EXAMINATEUR", "Examinateur"

    soutenance = models.ForeignKey(
        Soutenance,
        on_delete=models.CASCADE,
        related_name="membres"
    )

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="participations_jury"
    )

    fonction = models.CharField(
        max_length=20,
        choices=Fonction.choices,
        default=Fonction.EXAMINATEUR
    )

    present = models.BooleanField(
        default=True
    )

    date_ajout = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"{self.utilisateur.get_full_name() or self.utilisateur.username}"
            f" - {self.soutenance.projet.titre}"
        )


class Evaluation(models.Model):

    membre_jury = models.ForeignKey(
        MembreJury,
        on_delete=models.CASCADE,
        related_name="evaluations"
    )

    note = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    commentaire = models.TextField(
        blank=True
    )

    date_evaluation = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return (
            f"Évaluation - "
            f"{self.membre_jury.utilisateur.username}"
        )