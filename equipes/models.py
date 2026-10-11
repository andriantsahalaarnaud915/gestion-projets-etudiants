from django.db import models
from django.conf import settings
from projets.models import Projet

class Equipe(models.Model):
    nom = models.CharField(max_length=150)
    projet = models.OneToOneField(
        Projet,
        on_delete=models.CASCADE,
        related_name="equipe"
    )
    membres = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="equipes",
        blank=True
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Équipe - {self.projet.titre}"