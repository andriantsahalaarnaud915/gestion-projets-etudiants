from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings

from documents.models import Document
from .models import CorrectionIA
from .services import extraire_texte_document

from google import genai


@login_required
def corriger_document(request, document_id):

    document = get_object_or_404(
        Document,
        pk=document_id
    )

    # Récupérer la dernière correction existante
    correction = (
        CorrectionIA.objects
        .filter(document=document)
        .order_by("-date_creation")
        .first()
    )

    # Si aucune correction n'existe,
    # lancer automatiquement la première analyse
    if not correction:
        correction = lancer_correction_ia(
            document,
            request.user
        )

    # Récupérer tout l'historique
    corrections = (
        CorrectionIA.objects
        .filter(document=document)
        .order_by("-date_creation")
    )

    return render(
        request,
        "correction_ia/correction.html",
        {
            "document": document,
            "correction": correction,
            "corrections": corrections,
        }
    )


@login_required
def relancer_correction_ia(request, document_id):

    document = get_object_or_404(
        Document,
        pk=document_id
    )

    # La relance doit être effectuée en POST
    if request.method != "POST":
        return redirect(
            "corriger_document",
            document_id=document.id
        )

    # Créer une nouvelle correction
    # L'ancienne est conservée
    correction = lancer_correction_ia(
        document,
        request.user
    )

    # Récupérer tout l'historique
    corrections = (
        CorrectionIA.objects
        .filter(document=document)
        .order_by("-date_creation")
    )

    return render(
        request,
        "correction_ia/correction.html",
        {
            "document": document,
            "correction": correction,
            "corrections": corrections,
        }
    )


@login_required
def voir_correction_ia(request, correction_id):

    correction = get_object_or_404(
        CorrectionIA.objects.select_related(
            "document",
            "effectuee_par"
        ),
        pk=correction_id
    )

    document = correction.document

    # Historique complet du document
    corrections = (
        CorrectionIA.objects
        .filter(document=document)
        .order_by("-date_creation")
    )

    return render(
        request,
        "correction_ia/correction.html",
        {
            "document": document,
            "correction": correction,
            "corrections": corrections,
        }
    )


def lancer_correction_ia(document, utilisateur):

    # Créer une nouvelle correction
    correction = CorrectionIA.objects.create(
        document=document,
        effectuee_par=utilisateur,
        statut=CorrectionIA.Statut.EN_COURS
    )

    try:

        # Extraire le texte du document
        texte = extraire_texte_document(document)

        if not texte.strip():
            raise ValueError(
                "Impossible d'extraire du texte depuis ce document."
            )

        # Connexion à Gemini
        client = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )

        prompt = f"""
Tu es un assistant spécialisé dans la correction
et l'évaluation de documents académiques.

Analyse le document suivant.

DOCUMENT :
{texte}

Donne une analyse structurée contenant :

1. Résumé général
2. Qualité de la structure
3. Erreurs grammaticales et orthographiques
4. Problèmes de formulation
5. Incohérences détectées
6. Sections manquantes ou insuffisantes
7. Suggestions d'amélioration
8. Points forts
9. Points faibles
10. Note globale sur 100

Réponds en français avec des titres clairs.
"""

        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt
        )

        correction.resultat = response.text
        correction.statut = CorrectionIA.Statut.TERMINEE
        correction.save()

    except Exception as e:

        correction.statut = CorrectionIA.Statut.ERREUR
        correction.resultat = (
            f"Erreur lors de l'analyse : {str(e)}"
        )
        correction.save()

    return correction