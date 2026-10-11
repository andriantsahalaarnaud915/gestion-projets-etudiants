from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from projets.models import Projet
from projets.services_risque import calculer_risque_projet
from documents.models import Document
from equipes.models import Equipe
from django.http import JsonResponse


@login_required
def dashboard(request):

    user = request.user

    # ==========================================================
    # PROJETS DE L'UTILISATEUR
    # ==========================================================

    projets = (
        Projet.objects
        .filter(createur=user)
        .select_related("createur", "encadrant")
        .prefetch_related("jalons", "documents")
        .order_by("-date_creation")
    )

    total_projets = projets.count()

    # ==========================================================
    # STATISTIQUES
    # ==========================================================

    projets_en_cours = projets.filter(
        statut=Projet.Statut.EN_COURS
    ).count()

    projets_termines = projets.filter(
        statut__in=[
            Projet.Statut.EVALUE,
            Projet.Statut.CLOTURE,
        ]
    ).count()

    # ==========================================================
    # PROGRESSION MOYENNE
    # ==========================================================

    progression_moyenne = 0

    if total_projets > 0:
        progression_moyenne = round(
            sum(projet.progression for projet in projets)
            / total_projets
        )

    # ==========================================================
    # CALCUL DYNAMIQUE DES RISQUES
    # ==========================================================

    projets_a_risque = 0
    projets_moderes = 0
    projets_faibles = 0

    for projet in projets:

        risque = calculer_risque_projet(projet)

        # Attributs temporaires utilisés uniquement par le template
        projet.risque_dashboard = risque

        projet.score_risque_dashboard = risque["score"]
        projet.niveau_risque_dashboard = risque["libelle"]
        projet.classe_risque_dashboard = risque["classe_bootstrap"]

        projet.facteurs_risque_dashboard = risque["facteurs"]
        projet.contributions_risque_dashboard = risque["contributions"]

        if risque["niveau"] == "A_RISQUE":
            projets_a_risque += 1

        elif risque["niveau"] == "MODERE":
            projets_moderes += 1

        else:
            projets_faibles += 1

    # ==========================================================
    # DOCUMENTS
    # ==========================================================

    documents = (
        Document.objects
        .filter(projet__in=projets)
        .select_related(
            "projet",
            "depose_par"
        )
        .order_by("-date_depot")
    )

    total_documents = documents.count()

    documents_recents = documents[:5]

    # ==========================================================
    # PROJETS RECENTS
    # ==========================================================

    projets_recents = projets[:5]

    # ==========================================================
    # PROCHAINES ECHEANCES
    # ==========================================================

    aujourd_hui = timezone.localdate()

    prochaines_echeances = (
        projets
        .filter(
            date_fin_prevue__isnull=False,
            date_fin_prevue__gte=aujourd_hui
        )
        .order_by("date_fin_prevue")[:5]
    )

    # ==========================================================
    # EQUIPES
    # ==========================================================

    equipes = (
        Equipe.objects
        .filter(projet__in=projets)
        .prefetch_related("membres")
    )

    equipes_par_projet = {
        equipe.projet_id: equipe
        for equipe in equipes
    }

    # ==========================================================
    # PROJETS SANS ENCADRANT
    # ==========================================================

    projets_sans_encadrant = projets.filter(
        encadrant__isnull=True
    ).count()

    # ==========================================================
    # CONTEXT
    # ==========================================================

    context = {
        "user": user,

        # Projets
        "projets": projets,
        "projets_recents": projets_recents,

        # Statistiques
        "total_projets": total_projets,
        "projets_en_cours": projets_en_cours,
        "projets_termines": projets_termines,
        "progression_moyenne": progression_moyenne,

        # Risques
        "projets_a_risque": projets_a_risque,
        "projets_moderes": projets_moderes,
        "projets_faibles": projets_faibles,

        # Documents
        "documents": documents,
        "documents_recents": documents_recents,
        "total_documents": total_documents,

        # Échéances
        "prochaines_echeances": prochaines_echeances,

        # Équipes
        "equipes": equipes,
        "equipes_par_projet": equipes_par_projet,

        # Autres
        "projets_sans_encadrant": projets_sans_encadrant,

        "aujourd_hui": aujourd_hui,
    }

    return render(
        request,
        "dashboard/dashboard.html",
        context
    )
@login_required
def dashboard_api(request):
    user = request.user

    projets = (
        Projet.objects
        .filter(createur=user)
        .select_related("createur", "encadrant")
        .prefetch_related("jalons", "documents")
        .order_by("-date_creation")
    )

    total_projets = projets.count()

    projets_en_cours = projets.filter(
        statut=Projet.Statut.EN_COURS
    ).count()

    projets_termines = projets.filter(
        statut__in=[
            Projet.Statut.EVALUE,
            Projet.Statut.CLOTURE,
        ]
    ).count()

    # ----------------------------------------------------------
    # Progression moyenne
    # ----------------------------------------------------------

    progression_moyenne = 0

    if total_projets:
        progression_moyenne = round(
            sum(projet.progression for projet in projets)
            / total_projets
        )

    # ----------------------------------------------------------
    # Risques
    # ----------------------------------------------------------

    projets_a_risque = 0
    projets_moderes = 0
    projets_faibles = 0

    projets_data = []

    for projet in projets:

        risque = calculer_risque_projet(projet)

        if risque["niveau"] == "A_RISQUE":
            projets_a_risque += 1

        elif risque["niveau"] == "MODERE":
            projets_moderes += 1

        else:
            projets_faibles += 1

        projets_data.append({
            "id": projet.id,
            "titre": projet.titre,
            "statut": projet.get_statut_display(),
            "progression": projet.progression,
            "score_risque": risque["score"],
            "niveau_risque": risque["libelle"],
            "classe_risque": risque["classe_bootstrap"],
            "date_fin_prevue": (
                projet.date_fin_prevue.strftime("%d/%m/%Y")
                if projet.date_fin_prevue
                else None
            ),
        })

    # ----------------------------------------------------------
    # Documents
    # ----------------------------------------------------------

    documents = Document.objects.filter(
        projet__createur=user
    )

    total_documents = documents.count()

    # ----------------------------------------------------------
    # Réponse JSON
    # ----------------------------------------------------------

    return JsonResponse({
        "total_projets": total_projets,
        "projets_en_cours": projets_en_cours,
        "projets_termines": projets_termines,
        "progression_moyenne": progression_moyenne,

        "projets_a_risque": projets_a_risque,
        "projets_moderes": projets_moderes,
        "projets_faibles": projets_faibles,

        "total_documents": total_documents,

        "projets": projets_data,

        "actualise_a": timezone.localtime().strftime(
            "%d/%m/%Y %H:%M:%S"
        ),
    })