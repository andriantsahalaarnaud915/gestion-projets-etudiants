from django.contrib import admin
from .models import Equipe

@admin.register(Equipe)
class EquipeAdmin(admin.ModelAdmin):
    list_display = ("nom", "projet", "date_creation")
    filter_horizontal = ("membres",)