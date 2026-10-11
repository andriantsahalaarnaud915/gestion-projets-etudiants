from django.urls import path

from . import views


app_name = "jury"


urlpatterns = [

    # ==================================================
    # TABLEAU DE BORD JURY
    # ==================================================

    path(
        "",
        views.dashboard_jury,
        name="dashboard"
    ),


    # ==================================================
    # LISTE DES SOUTENANCES
    # ==================================================

    path(
        "soutenances/",
        views.liste_soutenances,
        name="liste_soutenances"
    ),


    # ==================================================
    # CRÉER UNE SOUTENANCE
    # ==================================================

    path(
        "soutenance/creer/",
        views.creer_soutenance,
        name="creer_soutenance"
    ),


    # ==================================================
    # DÉTAIL D'UNE SOUTENANCE
    # ==================================================

    path(
        "soutenance/<int:soutenance_id>/",
        views.detail_soutenance,
        name="detail_soutenance"
    ),


    # ==================================================
    # MODIFIER UNE SOUTENANCE
    # ==================================================

    path(
        "soutenance/<int:soutenance_id>/modifier/",
        views.modifier_soutenance,
        name="modifier_soutenance"
    ),


    # ==================================================
    # SUPPRIMER UNE SOUTENANCE
    # ==================================================

    path(
        "soutenance/<int:soutenance_id>/supprimer/",
        views.supprimer_soutenance,
        name="supprimer_soutenance"
    ),


    # ==================================================
    # AJOUTER UN MEMBRE DU JURY
    # ==================================================

    path(
        "soutenance/<int:soutenance_id>/jury/ajouter/",
        views.ajouter_membre_jury,
        name="ajouter_membre_jury"
    ),


    # ==================================================
    # SUPPRIMER UN MEMBRE DU JURY
    # ==================================================

    path(
        "jury/membre/<int:membre_id>/supprimer/",
        views.supprimer_membre_jury,
        name="supprimer_membre_jury"
    ),


    # ==================================================
    # ÉVALUATION
    # ==================================================

    path(
        "soutenance/<int:soutenance_id>/evaluation/",
        views.evaluer_soutenance,
        name="evaluer_soutenance"
    ),


    # ==================================================
    # CHANGEMENT DE STATUT
    # ==================================================

    path(
        "soutenance/<int:soutenance_id>/statut/",
        views.changer_statut_soutenance,
        name="changer_statut_soutenance"
    ),
]