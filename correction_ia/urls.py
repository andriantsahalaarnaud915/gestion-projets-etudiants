from django.urls import path
from . import views


urlpatterns = [

    path(
        "document/<int:document_id>/",
        views.corriger_document,
        name="corriger_document",
    ),

    path(
        "document/<int:document_id>/relancer/",
        views.relancer_correction_ia,
        name="relancer_correction_ia",
    ),

    path(
    "correction/<int:correction_id>/",
    views.voir_correction_ia,
    name="voir_correction_ia",
    ),
]
