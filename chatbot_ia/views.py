from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from django.db.models import Q

from projets.models import Projet

import json
from google import genai


@login_required
def chatbot(request):
    user = request.user

    projets = Projet.objects.filter(
        Q(createur=user) |
        Q(encadrant=user) |
        Q(equipe__membres=user)
    ).distinct()[:5]

    return render(
        request,
        "chatbot_ia/chatbot.html",
        {
            "projets": projets
        }
    )


@login_required
@require_POST
def chatbot_api(request):

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            "reponse": "❌ Le message envoyé est invalide."
        })

    message = data.get("message", "").strip()
    user = request.user

    if not message:
        return JsonResponse({
            "reponse": "Je n’ai pas compris votre message."
        })

    # Récupérer les projets de l'utilisateur
    projets = Projet.objects.filter(
        Q(createur=user) |
        Q(encadrant=user) |
        Q(equipe__membres=user)
    ).distinct()

    # Construire le contexte des projets
    contexte_projets = ""

    if projets.exists():

        lignes = []

        for p in projets:
            lignes.append(
                f"- {p.titre} | "
                f"Statut: {p.get_statut_display()} | "
                f"Progression: {p.progression}% | "
                f"Risque: {p.score_risque}/100 | "
                f"Encadrant: {p.encadrant or 'Non assigné'}"
            )

        contexte_projets = "\n".join(lignes)

    else:

        contexte_projets = (
            "L'utilisateur n'a actuellement aucun projet."
        )

    # Prompt système
    system_prompt = f"""
Tu es un assistant IA intelligent intégré dans une
plateforme de gestion de projets étudiants (M1 MIAGE).

Tu t'appelles "Assistant Projets IA".

Voici le contexte de l'utilisateur actuel :

- Nom : {user.get_full_name() or user.username}
- Rôle : {user.get_role_display()}

Projets de l'utilisateur :

{contexte_projets}

Tes règles :

- Réponds toujours en français.
- Sois professionnel, clair et utile.
- Base tes réponses sur le contexte des projets quand c'est pertinent.
- Tu peux donner des conseils méthodologiques.
- Tu peux analyser les risques des projets.
- Tu peux aider à préparer une soutenance.
- Tu peux aider à suivre l'avancement d'un projet.
- N'invente pas d'informations sur les projets qui n'existent pas.
- Si on te demande quelque chose hors sujet,
  ramène poliment la conversation vers les projets étudiants.
"""

    try:

        # Vérifier la clé API
        if not settings.GEMINI_API_KEY:
            return JsonResponse({
                "reponse": (
                    "⚠️ La clé API Gemini n'est pas configurée. "
                    "Contactez l'administrateur."
                )
            })

        # Client Gemini nouvelle API
        client = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )

        # Appel Gemini
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=f"""
{system_prompt}

Message de l'utilisateur :
{message}
"""
        )

        reponse_texte = response.text

    except Exception as e:

        reponse_texte = (
            "Désolé, une erreur est survenue avec l'IA : "
            f"{str(e)}"
        )

    return JsonResponse({
        "reponse": reponse_texte
    })