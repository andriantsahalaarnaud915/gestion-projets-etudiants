from django.contrib import admin
from .models import Soutenance, MembreJury, Evaluation


@admin.register(Soutenance)
class SoutenanceAdmin(admin.ModelAdmin):

    list_display = (
        "projet",
        "date",
        "heure",
        "salle",
        "statut",
    )

    list_filter = (
        "statut",
        "date",
    )

    search_fields = (
        "projet__titre",
        "salle",
    )

    ordering = (
        "date",
        "heure",
    )


@admin.register(MembreJury)
class MembreJuryAdmin(admin.ModelAdmin):

    list_display = (
        "soutenance",
        "utilisateur",
        "fonction",
        "present",
    )

    list_filter = (
        "fonction",
        "present",
    )

    search_fields = (
        "utilisateur__username",
        "utilisateur__first_name",
        "utilisateur__last_name",
        "soutenance__projet__titre",
    )


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):

    list_display = (
        "membre_jury",
        "note",
        "date_evaluation",
    )

    list_filter = (
        "date_evaluation",
    )

    search_fields = (
        "membre_jury__utilisateur__username",
        "membre_jury__soutenance__projet__titre",
    )