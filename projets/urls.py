from django.urls import path
from . import views


urlpatterns = [

    # ========================================================
    # PROJETS
    # ========================================================

    path(
        "",
        views.liste_projets,
        name="liste_projets"
    ),

    path(
        "creer/",
        views.creer_projet,
        name="creer_projet"
    ),

    path(
        "<int:pk>/",
        views.detail_projet,
        name="detail_projet"
    ),

    path(
        "<int:pk>/modifier/",
        views.modifier_projet,
        name="modifier_projet"
    ),

    path(
        "<int:pk>/supprimer/",
        views.supprimer_projet,
        name="supprimer_projet"
    ),


    # ========================================================
    # JALONS
    # ========================================================

    path(
        "<int:projet_id>/jalons/creer/",
        views.creer_jalon,
        name="creer_jalon"
    ),

    path(
        "jalons/<int:pk>/modifier/",
        views.modifier_jalon,
        name="modifier_jalon"
    ),

    path(
        "jalons/<int:pk>/supprimer/",
        views.supprimer_jalon,
        name="supprimer_jalon"
    ),

    path(
        "jalons/<int:pk>/valider/",
        views.valider_jalon,
        name="valider_jalon"
    ),


    # ========================================================
    # DOCUMENTS
    # ========================================================

    path(
        "<int:projet_id>/documents/deposer/",
        views.deposer_document,
        name="deposer_document"
    ),
]