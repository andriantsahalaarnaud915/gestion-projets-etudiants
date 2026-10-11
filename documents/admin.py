from django.contrib import admin
from .models import Document

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("titre", "type_document", "statut", "projet", "depose_par", "date_depot")
    list_filter = ("type_document", "statut")