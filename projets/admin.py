from django.contrib import admin
from .models import Projet, Jalon


@admin.register(Projet)
class ProjetAdmin(admin.ModelAdmin):

    list_display = (
        "titre",
        "createur",
        "statut",
        "progression",
        "date_fin_prevue",
        "date_creation",
    )

    list_filter = (
        "statut",
        "progression",
    )

    search_fields = (
        "titre",
        "description",
        "objectifs",
        "createur__username",
    )

    list_editable = (
        "statut",
        "progression",
    )

    ordering = (
        "-date_creation",
    )


@admin.register(Jalon)
class JalonAdmin(admin.ModelAdmin):

    list_display = (
        "__str__",
    )