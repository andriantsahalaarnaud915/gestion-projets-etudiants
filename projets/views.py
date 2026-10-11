from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .models import Projet, Jalon
from documents.models import Document
from accounts.models import User


# ============================================================
# OUTIL : VERIFICATION DES DROITS SUR LE PROJET
# ============================================================

def peut_gerer_projet(user, projet):
    """
    Vérifie si l'utilisateur peut gérer les informations générales
    du projet.
    """

    return (
        user.is_superuser
        or user.is_admin
        or projet.createur_id == user.id
        or (
            user.is_enseignant
            and projet.encadrant_id == user.id
        )
    )


def peut_modifier_suivi(user, projet):
    """
    Vérifie si l'utilisateur peut modifier le suivi du projet :

    - statut
    - jalons
    - validation des jalons
    - encadrant
    """

    return (
        user.is_superuser
        or user.is_admin
        or (
            user.is_enseignant
            and projet.encadrant_id == user.id
        )
    )


# ============================================================
# CYCLE DE VIE DU PROJET
# ============================================================

def obtenir_statuts_suivants(projet):
    """
    Retourne les statuts accessibles depuis le statut actuel.

    Cycle :

    PROPOSITION
        ↓
    VALIDE
        ↓
    EQUIPE_AFFECTEE
        ↓
    ENCADRANT_AFFECTE
        ↓
    EN_COURS
        ↓
    LIVRABLES_SOUMIS
        ↓
    VALIDATION_ENCADRANT
        ↓
    SOUTENANCE
        ↓
    EVALUE
        ↓
    CLOTURE
    """

    transitions = {

        Projet.Statut.PROPOSITION: [
            Projet.Statut.VALIDE,
            Projet.Statut.REFUSE,
        ],

        Projet.Statut.VALIDE: [
            Projet.Statut.EQUIPE_AFFECTEE,
            Projet.Statut.REFUSE,
        ],

        Projet.Statut.EQUIPE_AFFECTEE: [
            Projet.Statut.ENCADRANT_AFFECTE,
            Projet.Statut.REFUSE,
        ],

        Projet.Statut.ENCADRANT_AFFECTE: [
            Projet.Statut.EN_COURS,
            Projet.Statut.REFUSE,
        ],

        Projet.Statut.EN_COURS: [
            Projet.Statut.LIVRABLES_SOUMIS,
            Projet.Statut.REFUSE,
        ],

        Projet.Statut.LIVRABLES_SOUMIS: [
            Projet.Statut.VALIDATION_ENCADRANT,
            Projet.Statut.REFUSE,
        ],

        Projet.Statut.VALIDATION_ENCADRANT: [
            Projet.Statut.SOUTENANCE,
            Projet.Statut.REFUSE,
        ],

        Projet.Statut.SOUTENANCE: [
            Projet.Statut.EVALUE,
            Projet.Statut.REFUSE,
        ],

        Projet.Statut.EVALUE: [
            Projet.Statut.CLOTURE,
        ],

        Projet.Statut.CLOTURE: [],

        Projet.Statut.REFUSE: [
            Projet.Statut.PROPOSITION,
        ],
    }

    return transitions.get(
        projet.statut,
        []
    )


def transition_statut_autorisee(projet, nouveau_statut):
    """
    Vérifie si le passage vers le nouveau statut est autorisé.
    """

    if nouveau_statut == projet.statut:
        return True

    return nouveau_statut in obtenir_statuts_suivants(projet)


def libelle_statut(statut):
    """
    Retourne le libellé lisible d'un statut.
    """

    for valeur, label in Projet.Statut.choices:

        if valeur == statut:
            return label

    return statut


# ============================================================
# AUTOMATISATION DES JALONS EN RETARD
# ============================================================

def mettre_a_jour_retards_jalons(projet):
    """
    Détecte automatiquement les jalons dont la date prévue
    est dépassée.

    Un jalon déjà validé n'est jamais marqué en retard.

    Un jalon :
        - À faire
        - En cours
        - Terminé

    devient automatiquement :
        EN_RETARD

    si sa date prévue est dépassée.
    """

    aujourd_hui = timezone.now().date()

    jalons = projet.jalons.all()

    for jalon in jalons:

        # Un jalon validé reste validé
        if (
            jalon.statut == Jalon.Statut.VALIDE
            or jalon.valide
        ):
            continue

        if (
            jalon.date_prevue
            and jalon.date_prevue < aujourd_hui
            and jalon.statut != Jalon.Statut.EN_RETARD
        ):

            jalon.statut = Jalon.Statut.EN_RETARD

            jalon.save(
                update_fields=[
                    "statut"
                ]
            )


# ============================================================
# CALCUL AUTOMATIQUE DE LA PROGRESSION
# ============================================================

def mettre_a_jour_progression_projet(projet):
    """
    Calcule automatiquement la progression du projet
    à partir des jalons et de leur poids.

    Formule :

        Progression =
        Somme(poids × taux_achevement)
        / Somme(poids)

    Taux selon le statut du jalon :

        Validé  = 100 %
        Terminé = 100 %
        En cours = 40 %
        À faire = 0 %
        En retard = 0 %

    Aucun jalon :
        progression = 0 %
    """

    # Mettre d'abord à jour les retards
    mettre_a_jour_retards_jalons(projet)

    jalons = projet.jalons.all()

    poids_total = 0
    progression_ponderee = 0

    for jalon in jalons:

        # ----------------------------------------------------
        # POIDS
        # ----------------------------------------------------

        try:
            poids = int(
                jalon.poids or 0
            )

        except (
            TypeError,
            ValueError
        ):
            poids = 0

        if poids < 0:
            poids = 0

        # ----------------------------------------------------
        # TAUX D'ACHEVEMENT
        # ----------------------------------------------------

        try:
            taux = int(
                jalon.taux_achevement or 0
            )

        except (
            TypeError,
            ValueError
        ):
            taux = 0

        taux = max(
            0,
            min(100, taux)
        )

        # ----------------------------------------------------
        # CALCUL
        # ----------------------------------------------------

        poids_total += poids

        progression_ponderee += (
            poids * taux
        )

    # --------------------------------------------------------
    # PROGRESSION FINALE
    # --------------------------------------------------------

    if poids_total > 0:

        progression = round(
            progression_ponderee / poids_total
        )

    else:

        progression = 0

    progression = max(
        0,
        min(100, progression)
    )

    # --------------------------------------------------------
    # SAUVEGARDE
    # --------------------------------------------------------

    if projet.progression != progression:

        projet.progression = progression

        projet.save(
            update_fields=[
                "progression",
                "date_modification"
            ]
        )

    return progression


# ============================================================
# CALCUL DE LA VITESSE ET DE LA DATE DE FIN ESTIMEE
# ============================================================

def calculer_prevision_projet(projet):
    """
    Calcule :

    - jours écoulés
    - vitesse d'avancement
    - jours restants estimés
    - date de fin estimée
    - retard estimé en jours

    La formule utilisée est :

        Vitesse =
        progression / jours écoulés

        Jours nécessaires =
        (100 - progression) / vitesse

        Date fin estimée =
        aujourd'hui + jours nécessaires

        Retard =
        date fin estimée - date fin prévue
    """

    aujourd_hui = timezone.now().date()

    progression = mettre_a_jour_progression_projet(
        projet
    )

    date_debut = projet.date_debut

    # --------------------------------------------------------
    # JOURS ECOULES
    # --------------------------------------------------------

    if date_debut:

        jours_ecoules = (
            aujourd_hui - date_debut
        ).days

        jours_ecoules = max(
            0,
            jours_ecoules
        )

    else:

        jours_ecoules = 0

    # --------------------------------------------------------
    # VITESSE
    # --------------------------------------------------------

    vitesse = 0

    if jours_ecoules > 0 and progression > 0:

        vitesse = (
            progression / jours_ecoules
        )

    # --------------------------------------------------------
    # VALEURS PAR DEFAUT
    # --------------------------------------------------------

    jours_restants_estimes = None
    date_fin_estimee = None
    retard_estime = None

    # --------------------------------------------------------
    # CALCUL DATE FIN ESTIMEE
    # --------------------------------------------------------

    if vitesse > 0 and progression < 100:

        progression_restante = (
            100 - progression
        )

        jours_restants_estimes = round(
            progression_restante / vitesse
        )

        date_fin_estimee = (
            aujourd_hui
            + timezone.timedelta(
                days=jours_restants_estimes
            )
        )

    elif progression >= 100:

        date_fin_estimee = aujourd_hui

        jours_restants_estimes = 0

    # --------------------------------------------------------
    # CALCUL DU RETARD
    # --------------------------------------------------------

    if (
        date_fin_estimee
        and projet.date_fin_prevue
    ):

        retard_estime = (
            date_fin_estimee
            - projet.date_fin_prevue
        ).days

    return {
        "jours_ecoules": jours_ecoules,
        "vitesse": round(vitesse, 2),
        "jours_restants_estimes": jours_restants_estimes,
        "date_fin_estimee": date_fin_estimee,
        "retard_estime": retard_estime,
    }


# ============================================================
# LISTE DES PROJETS
# ============================================================

@login_required
def liste_projets(request):

    user = request.user

    if (
        user.is_enseignant
        or user.is_admin
        or user.is_superuser
    ):

        projets = Projet.objects.all()

    else:

        projets = (
            Projet.objects.filter(
                createur=user
            )
            | Projet.objects.filter(
                equipe__membres=user
            )
        ).distinct()

    return render(
        request,
        "projets/liste.html",
        {
            "projets": projets
        }
    )


# ============================================================
# CREER UN PROJET
# ============================================================

@login_required
def creer_projet(request):

    if request.method == "POST":

        titre = request.POST.get(
            "titre",
            ""
        ).strip()

        description = request.POST.get(
            "description",
            ""
        ).strip()

        objectifs = request.POST.get(
            "objectifs",
            ""
        ).strip()

        date_fin_prevue = (
            request.POST.get(
                "date_fin_prevue"
            )
            or None
        )

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not titre:

            messages.error(
                request,
                "Le titre du projet est obligatoire."
            )

            return render(
                request,
                "projets/creer.html"
            )

        if not description:

            messages.error(
                request,
                "La description du projet est obligatoire."
            )

            return render(
                request,
                "projets/creer.html"
            )

        # ----------------------------------------------------
        # CREATION
        # ----------------------------------------------------

        projet = Projet.objects.create(
            titre=titre,
            description=description,
            objectifs=objectifs,
            createur=request.user,
            statut=Projet.Statut.PROPOSITION,
            date_fin_prevue=date_fin_prevue
        )

        mettre_a_jour_progression_projet(
            projet
        )

        messages.success(
            request,
            "Projet créé avec succès !"
        )

        return redirect(
            "detail_projet",
            pk=projet.pk
        )

    return render(
        request,
        "projets/creer.html"
    )


# ============================================================
# DETAIL D'UN PROJET
# ============================================================

@login_required
def detail_projet(request, pk):

    projet = get_object_or_404(
        Projet,
        pk=pk
    )

    # --------------------------------------------------------
    # SYNCHRONISATION
    # --------------------------------------------------------

    mettre_a_jour_progression_projet(
        projet
    )

    # --------------------------------------------------------
    # PREVISION
    # --------------------------------------------------------

    prevision = calculer_prevision_projet(
        projet
    )

    # --------------------------------------------------------
    # JALONS
    # --------------------------------------------------------

    jalons = projet.jalons.all()

    # --------------------------------------------------------
    # STATUTS
    # --------------------------------------------------------

    statut_choices = Projet._meta.get_field(
        "statut"
    ).choices

    statuts_suivants = obtenir_statuts_suivants(
        projet
    )

    # --------------------------------------------------------
    # DROITS
    # --------------------------------------------------------

    peut_modifier_statut_progression = (
        peut_modifier_suivi(
            request.user,
            projet
        )
    )

    peut_modifier_projet = (
        peut_gerer_projet(
            request.user,
            projet
        )
    )

    return render(
        request,
        "projets/detail.html",
        {
            "projet": projet,
            "jalons": jalons,

            "statut_choices": statut_choices,
            "statuts_suivants": statuts_suivants,

            "peut_modifier_statut_progression": (
                peut_modifier_statut_progression
            ),

            "peut_modifier_projet": (
                peut_modifier_projet
            ),

            # Prévisions
            "prevision": prevision,
        }
    )


# ============================================================
# MODIFIER UN PROJET
# ============================================================

@login_required
def modifier_projet(request, pk):

    projet = get_object_or_404(
        Projet,
        pk=pk
    )

    # --------------------------------------------------------
    # DROITS GENERAUX
    # --------------------------------------------------------

    if not peut_gerer_projet(
        request.user,
        projet
    ):

        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier ce projet."
        )

        return redirect(
            "detail_projet",
            pk=projet.pk
        )

    # --------------------------------------------------------
    # DROIT DE MODIFIER LE SUIVI
    # --------------------------------------------------------

    peut_modifier_statut_progression = (
        peut_modifier_suivi(
            request.user,
            projet
        )
    )

    statut_choices = Projet._meta.get_field(
        "statut"
    ).choices

    statuts_valides = [
        valeur
        for valeur, label in statut_choices
    ]

    # --------------------------------------------------------
    # ENSEIGNANTS
    # --------------------------------------------------------

    enseignants = User.objects.filter(
        role=User.Role.ENSEIGNANT
    ).order_by(
        "last_name",
        "first_name",
        "username"
    )

    # --------------------------------------------------------
    # STATUTS ACCESSIBLES
    # --------------------------------------------------------

    statuts_suivants = obtenir_statuts_suivants(
        projet
    )

    # ========================================================
    # POST
    # ========================================================

    if request.method == "POST":

        # ----------------------------------------------------
        # INFORMATIONS GENERALES
        # ----------------------------------------------------

        titre = request.POST.get(
            "titre",
            projet.titre
        ).strip()

        description = request.POST.get(
            "description",
            projet.description
        ).strip()

        objectifs = request.POST.get(
            "objectifs",
            projet.objectifs
        ).strip()

        date_fin_prevue = (
            request.POST.get(
                "date_fin_prevue"
            )
            or None
        )

        # ----------------------------------------------------
        # VALIDATION TITRE
        # ----------------------------------------------------

        if not titre:

            messages.error(
                request,
                "Le titre du projet est obligatoire."
            )

            return render(
                request,
                "projets/modifier.html",
                {
                    "projet": projet,
                    "enseignants": enseignants,
                    "statut_choices": statut_choices,
                    "statuts_suivants": statuts_suivants,
                    "peut_modifier_statut_progression": (
                        peut_modifier_statut_progression
                    ),
                }
            )

        # ----------------------------------------------------
        # VALIDATION DESCRIPTION
        # ----------------------------------------------------

        if not description:

            messages.error(
                request,
                "La description du projet est obligatoire."
            )

            return render(
                request,
                "projets/modifier.html",
                {
                    "projet": projet,
                    "enseignants": enseignants,
                    "statut_choices": statut_choices,
                    "statuts_suivants": statuts_suivants,
                    "peut_modifier_statut_progression": (
                        peut_modifier_statut_progression
                    ),
                }
            )

        # ----------------------------------------------------
        # MISE A JOUR INFORMATIONS GENERALES
        # ----------------------------------------------------

        projet.titre = titre
        projet.description = description
        projet.objectifs = objectifs
        projet.date_fin_prevue = date_fin_prevue

        # ====================================================
        # ENCADRANT
        # ====================================================

        if peut_modifier_statut_progression:

            encadrant_id = request.POST.get(
                "encadrant"
            ) or None

            if encadrant_id:

                try:

                    encadrant_id = int(
                        encadrant_id
                    )

                    enseignant_existe = (
                        enseignants.filter(
                            id=encadrant_id
                        ).exists()
                    )

                    if not enseignant_existe:

                        messages.error(
                            request,
                            "L'encadrant sélectionné est invalide."
                        )

                        return render(
                            request,
                            "projets/modifier.html",
                            {
                                "projet": projet,
                                "enseignants": enseignants,
                                "statut_choices": statut_choices,
                                "statuts_suivants": statuts_suivants,
                                "peut_modifier_statut_progression": (
                                    peut_modifier_statut_progression
                                ),
                            }
                        )

                    projet.encadrant_id = encadrant_id

                except (
                    TypeError,
                    ValueError
                ):

                    messages.error(
                        request,
                        "L'encadrant sélectionné est invalide."
                    )

                    return render(
                        request,
                        "projets/modifier.html",
                        {
                            "projet": projet,
                            "enseignants": enseignants,
                            "statut_choices": statut_choices,
                            "statuts_suivants": statuts_suivants,
                            "peut_modifier_statut_progression": (
                                peut_modifier_statut_progression
                            ),
                        }
                    )

            else:

                projet.encadrant = None

        # ====================================================
        # STATUT
        # ====================================================

        if peut_modifier_statut_progression:

            nouveau_statut = request.POST.get(
                "statut",
                projet.statut
            )

            # ------------------------------------------------
            # STATUT INVALIDE
            # ------------------------------------------------

            if nouveau_statut not in statuts_valides:

                messages.error(
                    request,
                    "Le statut sélectionné est invalide."
                )

                return render(
                    request,
                    "projets/modifier.html",
                    {
                        "projet": projet,
                        "enseignants": enseignants,
                        "statut_choices": statut_choices,
                        "statuts_suivants": statuts_suivants,
                        "peut_modifier_statut_progression": (
                            peut_modifier_statut_progression
                        ),
                    }
                )

            # ------------------------------------------------
            # TRANSITION NON AUTORISEE
            # ------------------------------------------------

            if not transition_statut_autorisee(
                projet,
                nouveau_statut
            ):

                statut_actuel = libelle_statut(
                    projet.statut
                )

                statut_demande = libelle_statut(
                    nouveau_statut
                )

                messages.error(
                    request,
                    (
                        f"Transition impossible : "
                        f"« {statut_actuel} » → "
                        f"« {statut_demande} ». "
                        f"Vous devez respecter l'ordre "
                        f"du cycle de vie du projet."
                    )
                )

                return render(
                    request,
                    "projets/modifier.html",
                    {
                        "projet": projet,
                        "enseignants": enseignants,
                        "statut_choices": statut_choices,
                        "statuts_suivants": statuts_suivants,
                        "peut_modifier_statut_progression": (
                            peut_modifier_statut_progression
                        ),
                    }
                )

            # ------------------------------------------------
            # TRANSITION AUTORISEE
            # ------------------------------------------------

            projet.statut = nouveau_statut

        # ----------------------------------------------------
        # SAUVEGARDE
        # ----------------------------------------------------

        projet.save()

        # ----------------------------------------------------
        # RECALCUL PROGRESSION
        # ----------------------------------------------------

        mettre_a_jour_progression_projet(
            projet
        )

        messages.success(
            request,
            "Projet modifié avec succès !"
        )

        return redirect(
            "detail_projet",
            pk=projet.pk
        )

    # ========================================================
    # GET
    # ========================================================

    return render(
        request,
        "projets/modifier.html",
        {
            "projet": projet,
            "enseignants": enseignants,
            "statut_choices": statut_choices,
            "statuts_suivants": statuts_suivants,
            "peut_modifier_statut_progression": (
                peut_modifier_statut_progression
            ),
        }
    )


# ============================================================
# SUPPRIMER UN PROJET
# ============================================================

@login_required
def supprimer_projet(request, pk):

    projet = get_object_or_404(
        Projet,
        pk=pk
    )

    if not (
        request.user.is_superuser
        or request.user.is_admin
        or projet.createur_id == request.user.id
    ):

        messages.error(
            request,
            "Vous n'avez pas l'autorisation de supprimer ce projet."
        )

        return redirect(
            "detail_projet",
            pk=projet.pk
        )

    if request.method == "POST":

        projet.delete()

        messages.success(
            request,
            "Projet supprimé avec succès !"
        )

        return redirect(
            "liste_projets"
        )

    return render(
        request,
        "projets/supprimer.html",
        {
            "projet": projet
        }
    )


# ============================================================
# CREER UN JALON
# ============================================================

@login_required
def creer_jalon(request, projet_id):

    projet = get_object_or_404(
        Projet,
        pk=projet_id
    )

    if not peut_modifier_suivi(
        request.user,
        projet
    ):

        messages.error(
            request,
            "Vous n'avez pas l'autorisation de créer un jalon."
        )

        return redirect(
            "detail_projet",
            pk=projet.pk
        )

    # ========================================================
    # POST
    # ========================================================

    if request.method == "POST":

        titre = request.POST.get(
            "titre",
            ""
        ).strip()

        description = request.POST.get(
            "description",
            ""
        ).strip()

        date_prevue = request.POST.get(
            "date_prevue"
        )

        livrable_attendu = request.POST.get(
            "livrable_attendu",
            ""
        ).strip()

        commentaire = request.POST.get(
            "commentaire",
            ""
        ).strip()

        responsable_id = request.POST.get(
            "responsable"
        ) or None

        ordre_str = request.POST.get(
            "ordre",
            "1"
        )

        poids_str = request.POST.get(
            "poids",
            "1"
        )

        # ----------------------------------------------------
        # VALIDATION TITRE
        # ----------------------------------------------------

        if not titre:

            messages.error(
                request,
                "Le titre du jalon est obligatoire."
            )

            return render(
                request,
                "projets/jalon_creer.html",
                {
                    "projet": projet
                }
            )

        # ----------------------------------------------------
        # VALIDATION DATE
        # ----------------------------------------------------

        if not date_prevue:

            messages.error(
                request,
                "La date prévue du jalon est obligatoire."
            )

            return render(
                request,
                "projets/jalon_creer.html",
                {
                    "projet": projet
                }
            )

        # ----------------------------------------------------
        # VALIDATION ORDRE
        # ----------------------------------------------------

        try:

            ordre = int(
                ordre_str
            )

            if ordre < 1:
                ordre = 1

        except (
            TypeError,
            ValueError
        ):

            ordre = 1

        # ----------------------------------------------------
        # VALIDATION POIDS
        # ----------------------------------------------------

        try:

            poids = int(
                poids_str
            )

            if poids < 1:
                raise ValueError

        except (
            TypeError,
            ValueError
        ):

            messages.error(
                request,
                "Le poids du jalon doit être un nombre entier supérieur ou égal à 1."
            )

            return render(
                request,
                "projets/jalon_creer.html",
                {
                    "projet": projet
                }
            )

        # ----------------------------------------------------
        # RESPONSABLE
        # ----------------------------------------------------

        if responsable_id:

            try:

                responsable_id = int(
                    responsable_id
                )

            except (
                TypeError,
                ValueError
            ):

                responsable_id = None

        # ----------------------------------------------------
        # CREATION
        # ----------------------------------------------------

        jalon = Jalon.objects.create(
            projet=projet,
            titre=titre,
            description=description,
            date_prevue=date_prevue,
            livrable_attendu=livrable_attendu,
            commentaire=commentaire,
            responsable_id=responsable_id,
            ordre=ordre,
            poids=poids
        )

        # ----------------------------------------------------
        # RECALCUL
        # ----------------------------------------------------

        mettre_a_jour_progression_projet(
            projet
        )

        messages.success(
            request,
            f"Le jalon « {jalon.titre} » a été créé avec succès."
        )

        return redirect(
            "detail_projet",
            pk=projet.pk
        )

    # ========================================================
    # GET
    # ========================================================

    return render(
        request,
        "projets/jalon_creer.html",
        {
            "projet": projet
        }
    )


# ============================================================
# MODIFIER UN JALON
# ============================================================

@login_required
def modifier_jalon(request, pk):

    jalon = get_object_or_404(
        Jalon,
        pk=pk
    )

    projet = jalon.projet

    if not peut_modifier_suivi(
        request.user,
        projet
    ):

        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier ce jalon."
        )

        return redirect(
            "detail_projet",
            pk=projet.pk
        )

    statut_choices = Jalon._meta.get_field(
        "statut"
    ).choices

    statuts_valides = [
        valeur
        for valeur, label in statut_choices
    ]

    # ========================================================
    # POST
    # ========================================================

    if request.method == "POST":

        titre = request.POST.get(
            "titre",
            jalon.titre
        ).strip()

        if not titre:

            messages.error(
                request,
                "Le titre du jalon est obligatoire."
            )

            return render(
                request,
                "projets/jalon_modifier.html",
                {
                    "jalon": jalon,
                    "projet": projet,
                    "statut_choices": statut_choices,
                }
            )

        description = request.POST.get(
            "description",
            jalon.description
        ).strip()

        date_prevue = request.POST.get(
            "date_prevue"
        )

        if not date_prevue:

            messages.error(
                request,
                "La date prévue du jalon est obligatoire."
            )

            return render(
                request,
                "projets/jalon_modifier.html",
                {
                    "jalon": jalon,
                    "projet": projet,
                    "statut_choices": statut_choices,
                }
            )

        date_reelle = (
            request.POST.get(
                "date_reelle"
            )
            or None
        )

        livrable_attendu = request.POST.get(
            "livrable_attendu",
            jalon.livrable_attendu
        ).strip()

        commentaire = request.POST.get(
            "commentaire",
            jalon.commentaire
        ).strip()

        poids_str = request.POST.get(
            "poids",
            str(jalon.poids)
        )

        try:

            poids = int(
                poids_str
            )

            if poids < 1:
                raise ValueError

        except (
            TypeError,
            ValueError
        ):

            messages.error(
                request,
                "Le poids du jalon doit être un nombre entier supérieur ou égal à 1."
            )

            return render(
                request,
                "projets/jalon_modifier.html",
                {
                    "jalon": jalon,
                    "projet": projet,
                    "statut_choices": statut_choices,
                }
            )

        responsable_id = request.POST.get(
            "responsable"
        ) or None

        if responsable_id:

            try:

                responsable_id = int(
                    responsable_id
                )

            except (
                TypeError,
                ValueError
            ):

                responsable_id = None

        nouveau_statut = request.POST.get(
            "statut",
            jalon.statut
        )

        if nouveau_statut not in statuts_valides:

            messages.error(
                request,
                "Le statut du jalon sélectionné est invalide."
            )

            return render(
                request,
                "projets/jalon_modifier.html",
                {
                    "jalon": jalon,
                    "projet": projet,
                    "statut_choices": statut_choices,
                }
            )

        ordre_str = request.POST.get(
            "ordre",
            str(jalon.ordre)
        )

        try:

            ordre = max(
                1,
                int(ordre_str)
            )

        except (
            TypeError,
            ValueError
        ):

            ordre = jalon.ordre

        # ----------------------------------------------------
        # MISE A JOUR
        # ----------------------------------------------------

        jalon.titre = titre
        jalon.description = description
        jalon.date_prevue = date_prevue
        jalon.date_reelle = date_reelle
        jalon.livrable_attendu = livrable_attendu
        jalon.commentaire = commentaire
        jalon.poids = poids
        jalon.responsable_id = responsable_id
        jalon.statut = nouveau_statut
        jalon.ordre = ordre

        # ----------------------------------------------------
        # VALIDATION AUTOMATIQUE
        # ----------------------------------------------------

        if nouveau_statut == Jalon.Statut.VALIDE:

            jalon.valide = True

            if not jalon.date_reelle:

                jalon.date_reelle = (
                    timezone.now().date()
                )

        else:

            jalon.valide = False

        # ----------------------------------------------------
        # SAUVEGARDE
        # ----------------------------------------------------

        jalon.save()

        # ----------------------------------------------------
        # RECALCUL
        # ----------------------------------------------------

        mettre_a_jour_progression_projet(
            projet
        )

        messages.success(
            request,
            f"Le jalon « {jalon.titre} » a été modifié avec succès."
        )

        return redirect(
            "detail_projet",
            pk=projet.pk
        )

    # ========================================================
    # GET
    # ========================================================

    return render(
        request,
        "projets/jalon_modifier.html",
        {
            "jalon": jalon,
            "projet": projet,
            "statut_choices": statut_choices,
        }
    )


# ============================================================
# SUPPRIMER UN JALON
# ============================================================

@login_required
def supprimer_jalon(request, pk):

    jalon = get_object_or_404(
        Jalon,
        pk=pk
    )

    projet = jalon.projet

    if not peut_modifier_suivi(
        request.user,
        projet
    ):

        messages.error(
            request,
            "Vous n'avez pas l'autorisation de supprimer ce jalon."
        )

        return redirect(
            "detail_projet",
            pk=projet.pk
        )

    if request.method == "POST":

        titre = jalon.titre

        jalon.delete()

        mettre_a_jour_progression_projet(
            projet
        )

        messages.success(
            request,
            f"Le jalon « {titre} » a été supprimé."
        )

    return redirect(
        "detail_projet",
        pk=projet.pk
    )


# ============================================================
# MARQUER UN JALON COMME VALIDE
# ============================================================

@login_required
def valider_jalon(request, pk):

    jalon = get_object_or_404(
        Jalon,
        pk=pk
    )

    projet = jalon.projet

    if not peut_modifier_suivi(
        request.user,
        projet
    ):

        messages.error(
            request,
            "Vous n'avez pas l'autorisation de valider ce jalon."
        )

        return redirect(
            "detail_projet",
            pk=projet.pk
        )

    if request.method == "POST":

        jalon.statut = Jalon.Statut.VALIDE
        jalon.valide = True

        if not jalon.date_reelle:

            jalon.date_reelle = (
                timezone.now().date()
            )

        jalon.save()

        mettre_a_jour_progression_projet(
            projet
        )

        messages.success(
            request,
            f"Le jalon « {jalon.titre} » est maintenant validé."
        )

    return redirect(
        "detail_projet",
        pk=projet.pk
    )


# ============================================================
# DEPOSER UN DOCUMENT
# ============================================================

@login_required
def deposer_document(request, projet_id):

    projet = get_object_or_404(
        Projet,
        pk=projet_id
    )

    if request.method == "POST":

        titre = request.POST.get(
            "titre",
            ""
        ).strip()

        type_document = request.POST.get(
            "type_document"
        )

        fichier = request.FILES.get(
            "fichier"
        )

        commentaire = request.POST.get(
            "commentaire",
            ""
        ).strip()

        # ----------------------------------------------------
        # VALIDATION FICHIER
        # ----------------------------------------------------

        if not fichier:

            messages.error(
                request,
                "Veuillez sélectionner un fichier."
            )

            return render(
                request,
                "documents/deposer.html",
                {
                    "projet": projet
                }
            )

        # ----------------------------------------------------
        # VALIDATION TITRE
        # ----------------------------------------------------

        if not titre:

            messages.error(
                request,
                "Le titre du document est obligatoire."
            )

            return render(
                request,
                "documents/deposer.html",
                {
                    "projet": projet
                }
            )

        # ----------------------------------------------------
        # CREATION DOCUMENT
        # ----------------------------------------------------

        Document.objects.create(
            titre=titre,
            fichier=fichier,
            type_document=type_document,
            projet=projet,
            depose_par=request.user,
            commentaire=commentaire
        )

        messages.success(
            request,
            "Document déposé avec succès !"
        )

        return redirect(
            "detail_projet",
            pk=projet.pk
        )

    # ========================================================
    # GET
    # ========================================================

    return render(
        request,
        "documents/deposer.html",
        {
            "projet": projet
        }
    )