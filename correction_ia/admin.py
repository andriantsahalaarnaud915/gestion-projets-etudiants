from django.contrib import admin
from .models import CorrectionIA


@admin.register(CorrectionIA)
class CorrectionIAAdmin(admin.ModelAdmin):

    list_display = (
        "document",
        "effectuee_par",
        "statut",
        "date_creation",
    )

    list_filter = (
        "statut",
        "date_creation",
    )

    search_fields = (
        "document__titre",
        "effectuee_par__username",
    )

    readonly_fields = (
        "date_creation",
        "date_modification",
    )