from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from projets.models import Projet
from documents.models import Document
from equipes.models import Equipe


@login_required
def dashboard(request):

    user = request.user

    # =========================================================
    # PROJETS DE L'ETUDIANT
    # =========================================================

    projets = (
        Projet.objects
        .filter(
            createur=user
        )
        .select_related("createur", "encadrant")
        .order_by("-date_creation")
    )

    # =========================================================
    # STATISTIQUES
    # =========================================================

    total_projets = projets.count()

    projets_en_cours = projets.filter(
        statut=Projet.Statut.EN_COURS
    ).count()

    # CORRECTION : Statut.TERMINE n'existe pas.
    # Un projet est considere comme termine s'il est evalue ou cloture.
    projets_termines = projets.filter(
        statut__in=[
            Projet.Statut.EVALUE,
            Projet.Statut.CLOTURE,
        ]
    ).count()

    progression_moyenne = 0

    if total_projets > 0:
        progression_moyenne = round(
            sum(projet.progression for projet in projets)
            / total_projets
        )

    # =========================================================
    # DOCUMENTS
    # =========================================================

    documents = (
        Document.objects
        .filter(
            projet__in=projets
        )
        .select_related("projet", "depose_par")
        .order_by("-date_depot")
    )

    total_documents = documents.count()

    documents_recents = documents[:5]

    # =========================================================
    # PROJETS RECENTS
    # =========================================================

    projets_recents = projets[:5]

    # =========================================================
    # PROCHAINES ECHEANCES
    # =========================================================

    aujourd_hui = timezone.localdate()

    prochaines_echeances = (
        projets
        .filter(
            date_fin_prevue__isnull=False,
            date_fin_prevue__gte=aujourd_hui
        )
        .order_by("date_fin_prevue")[:5]
    )

    # =========================================================
    # EQUIPES
    # =========================================================

    equipes = (
        Equipe.objects
        .filter(
            projet__in=projets
        )
        .prefetch_related("membres")
    )

    equipes_par_projet = {
        equipe.projet_id: equipe
        for equipe in equipes
    }

    # =========================================================
    # CONTEXTE
    # =========================================================

    context = {
        "projets": projets,
        "projets_recents": projets_recents,

        "total_projets": total_projets,
        "projets_en_cours": projets_en_cours,
        "projets_termines": projets_termines,

        "progression_moyenne": progression_moyenne,

        "total_documents": total_documents,
        "documents_recents": documents_recents,

        "prochaines_echeances": prochaines_echeances,

        "equipes_par_projet": equipes_par_projet,
    }

    return render(
        request,
        "dashboard/dashboard.html",
        context
    )