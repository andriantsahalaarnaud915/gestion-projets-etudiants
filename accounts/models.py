from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrateur"
        ENSEIGNANT = "ENSEIGNANT", "Enseignant"
        ETUDIANT = "ETUDIANT", "Étudiant"
        JURY = "JURY", "Jury"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.ETUDIANT
    )
    telephone = models.CharField(max_length=20, blank=True, null=True)
    photo = models.ImageField(upload_to="photos/", blank=True, null=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_enseignant(self):
        return self.role == self.Role.ENSEIGNANT

    @property
    def is_etudiant(self):
        return self.role == self.Role.ETUDIANT

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser