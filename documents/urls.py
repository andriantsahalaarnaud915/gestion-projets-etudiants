from django.urls import path
from . import views

urlpatterns = [
    path("deposer/<int:projet_id>/", views.deposer_document, name="deposer_document"),
]