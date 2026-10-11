from django.db import models
from django.conf import settings
from django.utils import timezone


class Projet(models.Model):

    class Statut(models.TextChoices):
        PROPOSITION = "PROPOSITION", "Proposition"
        VALIDE = "VALIDE", "Validé"
        EQUIPE_AFFECTEE = "EQUIPE_AFFECTEE", "Équipe affectée"
        ENCADRANT_AFFECTE = "ENCADRANT_AFFECTE", "Encadrant affecté"
        EN_COURS = "EN_COURS", "En cours"
        LIVRABLES_SOUMIS = "LIVRABLES_SOUMIS", "Livrables soumis"
        VALIDATION_ENCADRANT = "VALIDATION_ENCADRANT", "Validation encadrant"
        SOUTENANCE = "SOUTENANCE", "Soutenance"
        EVALUE = "EVALUE", "Évalué"
        CLOTURE = "CLOTURE", "Clôturé"
        REFUSE = "REFUSE", "Refusé"

    titre = models.CharField(
        max_length=255
    )

    description = models.TextField()

    objectifs = models.TextField(
        blank=True
    )

    statut = models.CharField(
        max_length=30,
        choices=Statut.choices,
        default=Statut.PROPOSITION
    )

    # Progression automatique du projet : 0 à 100
    progression = models.PositiveIntegerField(
        default=0
    )

    # Score de risque : 0 à 100
    score_risque = models.PositiveIntegerField(
        default=0
    )

    date_debut = models.DateField(
        default=timezone.now
    )

    date_fin_prevue = models.DateField(
        null=True,
        blank=True
    )

    date_fin_reelle = models.DateField(
        null=True,
        blank=True
    )

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    date_modification = models.DateTimeField(
        auto_now=True
    )

    createur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="projets_crees"
    )

    encadrant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projets_encadres",
        limit_choices_to={
            "role": "ENSEIGNANT"
        }
    )

    def __str__(self):
        return self.titre

    # ==========================================================
    # GESTION DU RISQUE
    # ==========================================================

    @property
    def est_a_risque(self):
        """
        Indique si le projet est considéré comme à risque.

        Seuils du cahier des charges :
            0 à 29   : Faible
            30 à 59  : Modéré
            60 à 100 : À risque
        """
        return self.score_risque >= 60

    @property
    def niveau_risque(self):
        """
        Retourne le niveau de risque du projet.
        """

        if self.score_risque >= 60:
            return "À risque"

        if self.score_risque >= 30:
            return "Modéré"

        return "Faible"

    @property
    def classe_risque(self):
        """
        Retourne la classe Bootstrap correspondant
        au niveau de risque.
        """

        if self.score_risque >= 60:
            return "danger"

        if self.score_risque >= 30:
            return "warning"

        return "success"

    # ==========================================================
    # GESTION DES DATES
    # ==========================================================

    @property
    def jours_restants(self):
        """
        Retourne le nombre de jours restant avant
        la date de fin prévue.

        Valeur négative = projet en retard.
        """
        if self.date_fin_prevue:
            delta = (
                self.date_fin_prevue
                - timezone.now().date()
            )
            return delta.days

        return None

    @property
    def est_en_retard(self):
        """
        Indique si la date de fin prévue est dépassée.
        """

        if not self.date_fin_prevue:
            return False

        if self.date_fin_reelle:
            return False

        return self.date_fin_prevue < timezone.now().date()

    # ==========================================================
    # AFFICHAGE DE L'ÉTAT DU PROJET
    # ==========================================================

    @property
    def statut_libelle(self):
        """
        Retourne le libellé lisible du statut.
        """

        return self.get_statut_display()

    # ==========================================================
    # META
    # ==========================================================

    class Meta:
        ordering = [
            "-date_creation"
        ]


class Jalon(models.Model):

    class Statut(models.TextChoices):
        A_FAIRE = "A_FAIRE", "À faire"
        EN_COURS = "EN_COURS", "En cours"
        TERMINE = "TERMINE", "Terminé"
        EN_RETARD = "EN_RETARD", "En retard"
        VALIDE = "VALIDE", "Validé"

    projet = models.ForeignKey(
        Projet,
        on_delete=models.CASCADE,
        related_name="jalons"
    )

    titre = models.CharField(
        max_length=255
    )

    description = models.TextField(
        blank=True
    )

    date_prevue = models.DateField()

    date_reelle = models.DateField(
        null=True,
        blank=True
    )

    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jalons_responsables"
    )

    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.A_FAIRE
    )

    livrable_attendu = models.CharField(
        max_length=255,
        blank=True
    )

    # Commentaire de suivi ou remarque de l'encadrant
    commentaire = models.TextField(
        blank=True
    )

    # Poids du jalon dans la progression globale
    poids = models.PositiveIntegerField(
        default=1
    )

    valide = models.BooleanField(
        default=False
    )

    ordre = models.PositiveIntegerField(
        default=1
    )

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.titre} - {self.projet.titre}"

    # ==========================================================
    # PROGRESSION DU JALON
    # ==========================================================

    @property
    def taux_achevement(self):
        """
        Retourne le taux d'achèvement du jalon.

        VALIDE   = 100 %
        TERMINE  = 100 %
        EN_COURS = 40 %
        EN_RETARD = 0 %
        A_FAIRE  = 0 %
        """

        if self.statut == self.Statut.VALIDE:
            return 100

        if self.statut == self.Statut.TERMINE:
            return 100

        if self.statut == self.Statut.EN_COURS:
            return 40

        if self.statut == self.Statut.EN_RETARD:
            return 0

        return 0

    # ==========================================================
    # RETARD DU JALON
    # ==========================================================

    @property
    def est_en_retard(self):
        """
        Indique si le jalon est actuellement en retard.
        """

        if self.statut == self.Statut.VALIDE:
            return False

        if self.valide:
            return False

        if self.date_prevue:
            return (
                self.date_prevue < timezone.now().date()
            )

        return False

    # ==========================================================
    # LIBELLE DU STATUT
    # ==========================================================

    @property
    def statut_libelle(self):
        """
        Retourne le libellé lisible du statut.
        """

        return self.get_statut_display()

    # ==========================================================
    # META
    # ==========================================================

    class Meta:
        ordering = [
            "ordre",
            "date_prevue"
        ]