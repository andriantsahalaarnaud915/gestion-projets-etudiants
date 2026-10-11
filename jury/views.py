from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Avg

from .models import Soutenance, MembreJury, Evaluation
from projets.models import Projet
from accounts.models import User


# ============================================================
# VÉRIFICATION DES RÔLES
# ============================================================

def est_jury(user):
    """
    Vérifie si l'utilisateur est membre du jury.
    """
    return (
        user.is_authenticated
        and (
            user.is_superuser
            or getattr(user, "role", None) == "JURY"
        )
    )


def peut_gerer_soutenance(user):
    """
    Utilisateurs pouvant créer, modifier ou supprimer
    une soutenance.
    """
    if not user.is_authenticated:
        return False

    return (
        user.is_superuser
        or getattr(user, "role", None) in [
            "ADMIN",
            "ENSEIGNANT",
        ]
    )


def peut_consulter_soutenance(user):
    """
    Utilisateurs pouvant consulter les soutenances.
    """
    if not user.is_authenticated:
        return False

    return (
        user.is_superuser
        or getattr(user, "role", None) in [
            "ADMIN",
            "ENSEIGNANT",
            "JURY",
            "ETUDIANT",
        ]
    )


# ============================================================
# TABLEAU DE BORD JURY
# ============================================================

@login_required
def dashboard_jury(request):

    if not est_jury(request.user):
        raise PermissionDenied(
            "Accès réservé aux membres du jury."
        )

    soutenances = (
        Soutenance.objects
        .select_related(
            "projet",
            "creee_par"
        )
        .prefetch_related(
            "membres__utilisateur"
        )
        .order_by(
            "date",
            "heure"
        )
    )

    total_soutenances = soutenances.count()

    soutenances_planifiees = soutenances.filter(
        statut=Soutenance.Statut.PLANIFIEE
    ).count()

    soutenances_en_cours = soutenances.filter(
        statut=Soutenance.Statut.EN_COURS
    ).count()

    soutenances_terminees = soutenances.filter(
        statut=Soutenance.Statut.TERMINEE
    ).count()

    soutenances_annulees = soutenances.filter(
        statut=Soutenance.Statut.ANNULEE
    ).count()

    mes_soutenances = (
        soutenances
        .filter(
            membres__utilisateur=request.user
        )
        .distinct()
    )

    context = {
        "soutenances": soutenances,
        "mes_soutenances": mes_soutenances,
        "total_soutenances": total_soutenances,
        "soutenances_planifiees": soutenances_planifiees,
        "soutenances_en_cours": soutenances_en_cours,
        "soutenances_terminees": soutenances_terminees,
        "soutenances_annulees": soutenances_annulees,
    }

    return render(
        request,
        "jury/dashboard.html",
        context
    )


# ============================================================
# LISTE DES SOUTENANCES
# ============================================================

@login_required
def liste_soutenances(request):

    if not peut_consulter_soutenance(request.user):
        raise PermissionDenied(
            "Vous n'avez pas accès aux soutenances."
        )

    soutenances = (
        Soutenance.objects
        .select_related(
            "projet",
            "creee_par"
        )
        .prefetch_related(
            "membres__utilisateur"
        )
        .order_by(
            "date",
            "heure"
        )
    )

    # Un étudiant ne voit que les soutenances
    # liées à ses projets.
    if getattr(request.user, "role", None) == "ETUDIANT":
        soutenances = soutenances.filter(
            projet__createur=request.user
        )

    context = {
        "soutenances": soutenances,
        "peut_gerer": peut_gerer_soutenance(
            request.user
        ),
    }

    return render(
        request,
        "jury/liste_soutenances.html",
        context
    )


# ============================================================
# DÉTAIL D'UNE SOUTENANCE
# ============================================================

@login_required
def detail_soutenance(request, soutenance_id):

    if not peut_consulter_soutenance(request.user):
        raise PermissionDenied(
            "Vous n'avez pas accès aux soutenances."
        )

    soutenance = get_object_or_404(
        Soutenance.objects
        .select_related(
            "projet",
            "creee_par"
        )
        .prefetch_related(
            "membres__utilisateur",
            "membres__evaluations"
        ),
        pk=soutenance_id
    )

    # Un étudiant ne peut consulter que
    # les soutenances de ses propres projets.
    if (
        getattr(request.user, "role", None) == "ETUDIANT"
        and soutenance.projet.createur != request.user
    ):
        raise PermissionDenied(
            "Vous n'avez pas accès à cette soutenance."
        )

    evaluations = (
        Evaluation.objects
        .filter(
            membre_jury__soutenance=soutenance,
            note__isnull=False
        )
        .select_related(
            "membre_jury__utilisateur"
        )
    )

    moyenne = evaluations.aggregate(
        moyenne=Avg("note")
    )["moyenne"]

    nombre_evaluations = evaluations.count()

    # Membre du jury connecté.
    current_membre = (
        MembreJury.objects
        .filter(
            soutenance=soutenance,
            utilisateur=request.user
        )
        .first()
    )

    # Évaluation du membre connecté.
    current_evaluation = None

    if current_membre:
        current_evaluation = (
            Evaluation.objects
            .filter(
                membre_jury=current_membre
            )
            .first()
        )

    context = {
        "soutenance": soutenance,
        "evaluations": evaluations,
        "moyenne": moyenne,
        "nombre_evaluations": nombre_evaluations,

        # Variables utilisées par le template
        "current_membre": current_membre,
        "current_evaluation": current_evaluation,
        "peut_gerer_soutenance": peut_gerer_soutenance(
            request.user
        ),

        # Conservées également pour compatibilité
        "membre_connecte": current_membre,
        "peut_gerer": peut_gerer_soutenance(
            request.user
        ),
    }

    return render(
        request,
        "jury/detail_soutenance.html",
        context
    )


# ============================================================
# CRÉER UNE SOUTENANCE
# ============================================================

@login_required
def creer_soutenance(request):

    if not peut_gerer_soutenance(request.user):
        raise PermissionDenied(
            "Vous n'avez pas l'autorisation de créer une soutenance."
        )

    projets = (
        Projet.objects
        .all()
        .order_by("titre")
    )

    if request.method == "POST":

        projet_id = request.POST.get("projet")
        date = request.POST.get("date")
        heure = request.POST.get("heure")
        salle = request.POST.get(
            "salle",
            ""
        ).strip()

        statut = request.POST.get(
            "statut",
            Soutenance.Statut.PLANIFIEE
        )

        commentaire = request.POST.get(
            "commentaire",
            ""
        ).strip()

        # ----------------------------------------------------
        # VALIDATIONS
        # ----------------------------------------------------

        if not projet_id:

            messages.error(
                request,
                "Veuillez sélectionner un projet."
            )

        elif not date:

            messages.error(
                request,
                "Veuillez sélectionner une date."
            )

        elif not heure:

            messages.error(
                request,
                "Veuillez sélectionner une heure."
            )

        elif not salle:

            messages.error(
                request,
                "Veuillez renseigner la salle."
            )

        elif statut not in dict(
            Soutenance.Statut.choices
        ):

            messages.error(
                request,
                "Le statut sélectionné est invalide."
            )

        else:

            projet = get_object_or_404(
                Projet,
                pk=projet_id
            )

            soutenance = Soutenance.objects.create(
                projet=projet,
                date=date,
                heure=heure,
                salle=salle,
                statut=statut,
                commentaire=commentaire,
                creee_par=request.user,
            )

            messages.success(
                request,
                "La soutenance a été créée avec succès."
            )

            return redirect(
                "jury:detail_soutenance",
                soutenance_id=soutenance.id
            )

    context = {
        "projets": projets,
        "statut_choices": Soutenance.Statut.choices,
    }

    return render(
        request,
        "jury/form_soutenance.html",
        context
    )


# ============================================================
# MODIFIER UNE SOUTENANCE
# ============================================================

@login_required
def modifier_soutenance(
    request,
    soutenance_id
):

    if not peut_gerer_soutenance(request.user):
        raise PermissionDenied(
            "Vous n'avez pas l'autorisation de modifier cette soutenance."
        )

    soutenance = get_object_or_404(
        Soutenance,
        pk=soutenance_id
    )

    projets = (
        Projet.objects
        .all()
        .order_by("titre")
    )

    if request.method == "POST":

        projet_id = request.POST.get("projet")
        date = request.POST.get("date")
        heure = request.POST.get("heure")

        salle = request.POST.get(
            "salle",
            ""
        ).strip()

        statut = request.POST.get("statut")

        commentaire = request.POST.get(
            "commentaire",
            ""
        ).strip()

        if not projet_id:

            messages.error(
                request,
                "Veuillez sélectionner un projet."
            )

        elif not date:

            messages.error(
                request,
                "Veuillez sélectionner une date."
            )

        elif not heure:

            messages.error(
                request,
                "Veuillez sélectionner une heure."
            )

        elif not salle:

            messages.error(
                request,
                "Veuillez renseigner la salle."
            )

        elif statut not in dict(
            Soutenance.Statut.choices
        ):

            messages.error(
                request,
                "Le statut sélectionné est invalide."
            )

        else:

            projet = get_object_or_404(
                Projet,
                pk=projet_id
            )

            soutenance.projet = projet
            soutenance.date = date
            soutenance.heure = heure
            soutenance.salle = salle
            soutenance.statut = statut
            soutenance.commentaire = commentaire

            soutenance.save()

            messages.success(
                request,
                "La soutenance a été modifiée avec succès."
            )

            return redirect(
                "jury:detail_soutenance",
                soutenance_id=soutenance.id
            )

    context = {
        "soutenance": soutenance,
        "projets": projets,
        "statut_choices": Soutenance.Statut.choices,
    }

    return render(
        request,
        "jury/form_soutenance.html",
        context
    )


# ============================================================
# SUPPRIMER UNE SOUTENANCE
# ============================================================

@login_required
def supprimer_soutenance(
    request,
    soutenance_id
):

    if not peut_gerer_soutenance(request.user):
        raise PermissionDenied(
            "Vous n'avez pas l'autorisation de supprimer cette soutenance."
        )

    soutenance = get_object_or_404(
        Soutenance,
        pk=soutenance_id
    )

    if request.method == "POST":

        soutenance.delete()

        messages.success(
            request,
            "La soutenance a été supprimée."
        )

        return redirect(
            "jury:liste_soutenances"
        )

    return render(
        request,
        "jury/confirmer_suppression.html",
        {
            "soutenance": soutenance
        }
    )


# ============================================================
# AJOUTER UN MEMBRE DU JURY
# ============================================================

@login_required
def ajouter_membre_jury(
    request,
    soutenance_id
):

    if not peut_gerer_soutenance(request.user):
        raise PermissionDenied(
            "Vous n'avez pas l'autorisation de gérer le jury."
        )

    soutenance = get_object_or_404(
        Soutenance,
        pk=soutenance_id
    )

    if request.method == "POST":

        utilisateur_id = request.POST.get(
            "utilisateur"
        )

        fonction = request.POST.get(
            "fonction",
            MembreJury.Fonction.EXAMINATEUR
        )

        if not utilisateur_id:

            messages.error(
                request,
                "Veuillez sélectionner un membre du jury."
            )

        elif fonction not in dict(
            MembreJury.Fonction.choices
        ):

            messages.error(
                request,
                "La fonction sélectionnée est invalide."
            )

        else:

            utilisateur = get_object_or_404(
                User,
                pk=utilisateur_id,
                role="JURY"
            )

            membre, created = (
                MembreJury.objects.get_or_create(
                    soutenance=soutenance,
                    utilisateur=utilisateur,
                    defaults={
                        "fonction": fonction,
                        "present": True,
                    }
                )
            )

            if not created:

                membre.fonction = fonction
                membre.save()

                messages.success(
                    request,
                    "La fonction du membre du jury a été mise à jour."
                )

            else:

                messages.success(
                    request,
                    "Le membre du jury a été ajouté."
                )

    return redirect(
        "jury:detail_soutenance",
        soutenance_id=soutenance.id
    )


# ============================================================
# SUPPRIMER UN MEMBRE DU JURY
# ============================================================

@login_required
def supprimer_membre_jury(
    request,
    membre_id
):

    if not peut_gerer_soutenance(request.user):
        raise PermissionDenied(
            "Vous n'avez pas l'autorisation de gérer le jury."
        )

    membre = get_object_or_404(
        MembreJury,
        pk=membre_id
    )

    soutenance_id = membre.soutenance.id

    if request.method == "POST":

        membre.delete()

        messages.success(
            request,
            "Le membre a été retiré du jury."
        )

    return redirect(
        "jury:detail_soutenance",
        soutenance_id=soutenance_id
    )


# ============================================================
# ÉVALUER UNE SOUTENANCE
# ============================================================

@login_required
def evaluer_soutenance(
    request,
    soutenance_id
):

    if not est_jury(request.user):
        raise PermissionDenied(
            "Accès réservé aux membres du jury."
        )

    soutenance = get_object_or_404(
        Soutenance,
        pk=soutenance_id
    )

    membre_jury = get_object_or_404(
        MembreJury,
        soutenance=soutenance,
        utilisateur=request.user
    )

    evaluation = (
        Evaluation.objects
        .filter(
            membre_jury=membre_jury
        )
        .first()
    )

    if request.method == "POST":

        note = request.POST.get("note")

        commentaire = request.POST.get(
            "commentaire",
            ""
        ).strip()

        if not note:

            messages.error(
                request,
                "Veuillez renseigner une note."
            )

        else:

            try:

                note_float = float(note)

                if note_float < 0 or note_float > 20:

                    messages.error(
                        request,
                        "La note doit être comprise entre 0 et 20."
                    )

                    return redirect(
                        "jury:evaluer_soutenance",
                        soutenance_id=soutenance.id
                    )

            except ValueError:

                messages.error(
                    request,
                    "La note doit être numérique."
                )

                return redirect(
                    "jury:evaluer_soutenance",
                    soutenance_id=soutenance.id
                )

            Evaluation.objects.update_or_create(
                membre_jury=membre_jury,
                defaults={
                    "note": note,
                    "commentaire": commentaire,
                }
            )

            messages.success(
                request,
                "Votre évaluation a été enregistrée."
            )

            return redirect(
                "jury:detail_soutenance",
                soutenance_id=soutenance.id
            )

    return render(
        request,
        "jury/evaluation.html",
        {
            "soutenance": soutenance,
            "membre_jury": membre_jury,
            "evaluation": evaluation,
        }
    )


# ============================================================
# CHANGER LE STATUT D'UNE SOUTENANCE
# ============================================================

@login_required
def changer_statut_soutenance(
    request,
    soutenance_id
):

    if not peut_gerer_soutenance(request.user):
        raise PermissionDenied(
            "Vous n'avez pas l'autorisation de modifier le statut."
        )

    soutenance = get_object_or_404(
        Soutenance,
        pk=soutenance_id
    )

    if request.method != "POST":

        return redirect(
            "jury:detail_soutenance",
            soutenance_id=soutenance.id
        )

    nouveau_statut = request.POST.get(
        "statut"
    )

    statuts_autorises = {
        Soutenance.Statut.PLANIFIEE,
        Soutenance.Statut.EN_COURS,
        Soutenance.Statut.TERMINEE,
        Soutenance.Statut.ANNULEE,
    }

    if nouveau_statut not in statuts_autorises:

        messages.error(
            request,
            "Statut invalide."
        )

        return redirect(
            "jury:detail_soutenance",
            soutenance_id=soutenance.id
        )

    soutenance.statut = nouveau_statut

    soutenance.save(
        update_fields=[
            "statut",
            "date_modification",
        ]
    )

    messages.success(
        request,
        "Le statut de la soutenance a été mis à jour."
    )

    return redirect(
        "jury:detail_soutenance",
        soutenance_id=soutenance.id
    )