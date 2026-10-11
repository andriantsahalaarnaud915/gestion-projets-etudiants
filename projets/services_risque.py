from collections import Counter
from datetime import timedelta

from django.utils import timezone


# ============================================================
# CONFIGURATION DU SCORE DE RISQUE
# ============================================================

POIDS_RISQUE = {
    "retard": 25,
    "faible_progression": 20,
    "livrables_non_deposes": 20,
    "absence_activite": 15,
    "documents_rejetes": 10,
    "echeance_proche": 10,
}

SEUIL_FAIBLE = 30
SEUIL_MODERE = 60

JOURS_INACTIVITE = 14
JOURS_ECHEANCE_PROCHE = 7


# ============================================================
# OUTILS GENERAUX
# ============================================================

def limiter_score(valeur):
    """
    Garantit qu'un score reste compris entre 0 et 100.
    """
    return max(0, min(100, round(valeur)))


def niveau_risque(score):
    """
    Retourne le niveau technique du risque.
    """
    score = limiter_score(score)

    if score >= SEUIL_MODERE:
        return "A_RISQUE"

    if score >= SEUIL_FAIBLE:
        return "MODERE"

    return "FAIBLE"


def libelle_niveau_risque(score):
    """
    Retourne le libellé affichable.
    """
    niveau = niveau_risque(score)

    return {
        "FAIBLE": "Faible",
        "MODERE": "Modéré",
        "A_RISQUE": "Projet à risque",
    }[niveau]


def classe_bootstrap_risque(score):
    """
    Retourne une classe Bootstrap adaptée au niveau de risque.
    """
    niveau = niveau_risque(score)

    return {
        "FAIBLE": "success",
        "MODERE": "warning",
        "A_RISQUE": "danger",
    }[niveau]


# ============================================================
# FACTEUR 1 : RETARD
# Poids : 25 %
# ============================================================

def calculer_facteur_retard(projet):
    """
    Évalue le risque lié aux retards des jalons
    et au retard estimé du projet.
    """

    jalons = list(projet.jalons.all())

    if not jalons:
        return 0

    aujourd_hui = timezone.now().date()

    # --------------------------------------------------------
    # 1. Retard des jalons
    # --------------------------------------------------------

    jalons_en_retard = []

    for jalon in jalons:
        if jalon.statut == "EN_RETARD":
            jalons_en_retard.append(jalon)

        elif (
            jalon.date_prevue
            and jalon.date_prevue < aujourd_hui
            and not jalon.valide
        ):
            jalons_en_retard.append(jalon)

    ratio_retard = (
        len(jalons_en_retard) / len(jalons)
    ) * 100

    # --------------------------------------------------------
    # 2. Retard estimé du projet
    # --------------------------------------------------------

    retard_estime = 0

    if projet.date_fin_prevue:

        progression = projet.progression or 0

        if progression >= 100:

            date_fin_estimee = aujourd_hui

        else:

            jours_ecoules = max(
                1,
                (aujourd_hui - projet.date_debut).days
            )

            vitesse = progression / jours_ecoules

            if vitesse > 0:

                jours_restants = (
                    (100 - progression) / vitesse
                )

                date_fin_estimee = (
                    aujourd_hui
                    + timedelta(days=round(jours_restants))
                )

                retard_estime = max(
                    0,
                    (
                        date_fin_estimee
                        - projet.date_fin_prevue
                    ).days
                )

    # 5 points de risque par jour de retard,
    # plafonné à 100.
    score_retard_estime = min(
        100,
        retard_estime * 5
    )

    return limiter_score(
        max(
            ratio_retard,
            score_retard_estime
        )
    )


# ============================================================
# FACTEUR 2 : FAIBLE PROGRESSION
# Poids : 20 %
# ============================================================

def calculer_facteur_faible_progression(projet):
    """
    Compare la progression réelle à la progression
    théorique attendue selon les dates du projet.
    """

    if not projet.date_fin_prevue:
        return 0

    aujourd_hui = timezone.now().date()

    date_debut = projet.date_debut
    date_fin = projet.date_fin_prevue

    duree_totale = (
        date_fin - date_debut
    ).days

    if duree_totale <= 0:
        return 0

    jours_ecoules = (
        aujourd_hui - date_debut
    ).days

    jours_ecoules = max(
        0,
        min(
            jours_ecoules,
            duree_totale
        )
    )

    progression_attendue = (
        jours_ecoules / duree_totale
    ) * 100

    progression_reelle = (
        projet.progression or 0
    )

    ecart = (
        progression_attendue
        - progression_reelle
    )

    if ecart <= 0:
        return 0

    return limiter_score(ecart)


# ============================================================
# FACTEUR 3 : LIVRABLES NON DÉPOSÉS
# Poids : 20 %
# ============================================================

def calculer_facteur_livrables_non_deposes(projet):
    """
    Évalue les livrables attendus dont les jalons sont arrivés
    à échéance mais qui ne sont pas encore validés.

    Comme Document n'est pas directement lié à Jalon,
    la correspondance est estimée au niveau du projet.
    """

    aujourd_hui = timezone.now().date()

    jalons_attendus = [
        jalon
        for jalon in projet.jalons.all()
        if (
            jalon.livrable_attendu
            and jalon.date_prevue
            and jalon.date_prevue <= aujourd_hui
            and not jalon.valide
        )
    ]

    if not jalons_attendus:
        return 0

    nombre_attendus = len(jalons_attendus)

    # Documents effectivement déposés pour le projet.
    documents_deposes = projet.documents.filter(
        date_depot__date__lte=aujourd_hui
    ).count()

    # Nombre de livrables considérés comme non déposés.
    non_deposes = max(
        0,
        nombre_attendus - documents_deposes
    )

    return limiter_score(
        (non_deposes / nombre_attendus) * 100
    )


# ============================================================
# FACTEUR 4 : ABSENCE D'ACTIVITÉ
# Poids : 15 %
# ============================================================

def calculer_facteur_absence_activite(projet):
    """
    Évalue l'inactivité récente du projet.

    Les dernières activités prises en compte sont :
    - dépôt d'un document ;
    - dernière connexion du créateur ;
    - dernière connexion de l'encadrant ;
    - dernière connexion d'un membre de l'équipe.
    """

    aujourd_hui = timezone.now()

    dates_activite = []

    # --------------------------------------------------------
    # Documents
    # --------------------------------------------------------

    dernier_document = (
        projet.documents
        .order_by("-date_depot")
        .first()
    )

    if dernier_document and dernier_document.date_depot:
        dates_activite.append(
            dernier_document.date_depot
        )

    # --------------------------------------------------------
    # Créateur
    # --------------------------------------------------------

    if (
        projet.createur
        and projet.createur.last_login
    ):
        dates_activite.append(
            projet.createur.last_login
        )

    # --------------------------------------------------------
    # Encadrant
    # --------------------------------------------------------

    if (
        projet.encadrant
        and projet.encadrant.last_login
    ):
        dates_activite.append(
            projet.encadrant.last_login
        )

    # --------------------------------------------------------
    # Membres de l'équipe
    # --------------------------------------------------------

    try:

        membres = projet.equipe.membres.all()

        for membre in membres:

            if membre.last_login:
                dates_activite.append(
                    membre.last_login
                )

    except Exception:
        # Un projet peut ne pas encore avoir d'équipe.
        pass

    # --------------------------------------------------------
    # Aucune activité connue
    # --------------------------------------------------------

    if not dates_activite:

        dernier = projet.date_creation

        if not dernier:
            return 100

    else:

        dernier = max(dates_activite)

    anciennete = (
        aujourd_hui - dernier
    ).days

    if anciennete < JOURS_INACTIVITE:
        return 0

    score = (
        anciennete
        / (JOURS_INACTIVITE * 2)
    ) * 100

    return limiter_score(score)


# ============================================================
# FACTEUR 5 : DOCUMENTS REJETÉS
# Poids : 10 %
# ============================================================

def calculer_facteur_documents_rejetes(projet):
    """
    Évalue la proportion de documents refusés.

    Une répétition du même titre refusé au moins deux fois
    augmente le facteur de risque à 100.
    """

    documents = list(
        projet.documents.all()
    )

    if not documents:
        return 0

    documents_rejetes = [
        document
        for document in documents
        if document.statut == "REFUSE"
    ]

    if not documents_rejetes:
        return 0

    ratio_rejet = (
        len(documents_rejetes)
        / len(documents)
    ) * 100

    # Recherche des documents refusés plusieurs fois
    # avec le même titre.
    titres = Counter(
        document.titre
        for document in documents_rejetes
        if document.titre
    )

    repetitions = [
        nombre
        for nombre in titres.values()
        if nombre >= 2
    ]

    score_repetition = (
        100
        if repetitions
        else 0
    )

    return limiter_score(
        max(
            ratio_rejet,
            score_repetition
        )
    )


# ============================================================
# FACTEUR 6 : ÉCHÉANCE PROCHE
# Poids : 10 %
# ============================================================

def calculer_facteur_echeance_proche(projet):
    """
    Évalue le risque lorsqu'un jalon non terminé
    arrive à échéance dans les 7 prochains jours.
    """

    aujourd_hui = timezone.now().date()

    date_limite = (
        aujourd_hui
        + timedelta(
            days=JOURS_ECHEANCE_PROCHE
        )
    )

    jalons = projet.jalons.filter(
        date_prevue__gte=aujourd_hui,
        date_prevue__lte=date_limite
    )

    jalons_a_risque = [
        jalon
        for jalon in jalons
        if (
            jalon.statut
            in (
                "A_FAIRE",
                "EN_COURS",
            )
            and not jalon.valide
        )
    ]

    if not jalons_a_risque:
        return 0

    scores = []

    for jalon in jalons_a_risque:

        jours = (
            jalon.date_prevue
            - aujourd_hui
        ).days

        if jours <= 0:

            score = 100

        else:

            score = (
                (
                    JOURS_ECHEANCE_PROCHE
                    - jours
                )
                / JOURS_ECHEANCE_PROCHE
            ) * 100

        scores.append(score)

    return limiter_score(
        max(scores)
    )


# ============================================================
# CALCUL GLOBAL DU RISQUE
# ============================================================

def calculer_risque_projet(projet):
    """
    Calcule le score global du risque du projet.

    Formule :

    Score =
        retard × 25 %
        + faible progression × 20 %
        + livrables non déposés × 20 %
        + absence activité × 15 %
        + documents rejetés × 10 %
        + échéance proche × 10 %
    """

    facteurs = {
        "retard": calculer_facteur_retard(projet),

        "faible_progression":
            calculer_facteur_faible_progression(projet),

        "livrables_non_deposes":
            calculer_facteur_livrables_non_deposes(projet),

        "absence_activite":
            calculer_facteur_absence_activite(projet),

        "documents_rejetes":
            calculer_facteur_documents_rejetes(projet),

        "echeance_proche":
            calculer_facteur_echeance_proche(projet),
    }

    # --------------------------------------------------------
    # Contributions pondérées
    # --------------------------------------------------------

    contributions = {}

    for nom, valeur in facteurs.items():

        contributions[nom] = (
            valeur
            * POIDS_RISQUE[nom]
            / 100
        )

    # --------------------------------------------------------
    # Score global
    # --------------------------------------------------------

    score = limiter_score(
        sum(contributions.values())
    )

    return {
        "score": score,

        "niveau": niveau_risque(
            score
        ),

        "libelle": libelle_niveau_risque(
            score
        ),

        "classe_bootstrap":
            classe_bootstrap_risque(
                score
            ),

        "facteurs": facteurs,

        "contributions": contributions,

        "poids": POIDS_RISQUE,
    }


# ============================================================
# RECALCUL DU SCORE EN BASE
# ============================================================

def recalculer_risque_projet(projet):
    """
    Calcule le risque puis met à jour Projet.score_risque
    uniquement si la valeur a changé.
    """

    resultat = calculer_risque_projet(
        projet
    )

    nouveau_score = resultat["score"]

    if projet.score_risque != nouveau_score:

        projet.score_risque = nouveau_score

        projet.save(
            update_fields=[
                "score_risque"
            ]
        )

    return resultat


# ============================================================
# RECALCUL DE PLUSIEURS PROJETS
# ============================================================

def recalculer_risques_projets(projets):
    """
    Recalcule les risques d'une liste ou d'un QuerySet
    de projets.
    """

    resultats = []

    for projet in projets:

        resultats.append(
            recalculer_risque_projet(
                projet
            )
        )

    return resultats