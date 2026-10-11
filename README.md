Plateforme web de gestion des projets étudiants
Projet professionnel de Master 1 MIAGE
Présentation
Cette application web permet de gérer le cycle de vie des projets étudiants, depuis la proposition du projet jusqu'à sa clôture et sa soutenance.
Objectifs
- Centraliser les projets étudiants.
- Suivre l'avancement des projets et des jalons.
- Gérer les documents et livrables.
- Organiser les soutenances et les membres du jury.
- Fournir des tableaux de bord adaptés aux différents rôles.
- Intégrer des fonctionnalités d'intelligence artificielle pour l'assistance au suivi et la correction de documents.
Technologies
- Python
- Django
- SQLite pour la base de données actuelle
- HTML / CSS
- Bootstrap
- JavaScript
- Gemini pour les fonctionnalités d'intelligence artificielle
Principaux modules
accounts/
projets/
equipes/
documents/
dashboard/
chatbot_ia/
correction_ia/
jury/
config/
Rôles
- Administrateur
- Enseignant / encadrant
- Étudiant
- Membre du jury
Installation
1. Cloner le projet
git clone <URL_DU_DEPOT>
cd <NOM_DU_PROJET>
2. Créer un environnement virtuel
Windows :
python -m venv venv
venv\Scripts\activate
Linux / macOS :
python3 -m venv venv
source venv/bin/activate
3. Installer les dépendances
pip install -r requirements.txt
4. Configurer la clé Gemini
La clé API Gemini doit être configurée comme variable d'environnement.
Windows PowerShell :
$env:GEMINI_API_KEY="VOTRE_CLE_API"
Linux / macOS :
export GEMINI_API_KEY="VOTRE_CLE_API"
Ne jamais publier une clé API directement dans Git.
5. Vérifier le projet
python manage.py check
6. Appliquer les migrations
python manage.py migrate
Si le dépôt contient déjà une base SQLite fonctionnelle et des migrations appliquées, ne supprimez pas db.sqlite3.

7. Lancer le serveur
python manage.py runserver
Puis ouvrir :
http://127.0.0.1:8000/
Fonctionnalités
Gestion des projets
- Création et modification des projets.
- Affectation d'un encadrant.
- Gestion du cycle de vie.
- Suivi de l'avancement.
- Gestion des jalons.
- Estimation des retards.
Gestion des documents
- Dépôt de documents.
- Suivi du statut des documents.
- Validation / rejet des livrables.
- Commentaires.
Soutenances et jury
- Création d'une soutenance.
- Modification et suppression.
- Gestion de la date, de l'heure et de la salle.
- Ajout des membres du jury.
- Gestion des fonctions du jury.
- Évaluation individuelle.
- Calcul de la moyenne des évaluations.
Intelligence artificielle
- Assistant IA pour le suivi des projets.
- Assistance aux étudiants.
- Assistance au suivi des projets.
- Correction intelligente des documents.
Structure générale
Utilisateur
    |
    v
Interface Django Templates
    |
    v
Applications Django
    |
    +-- accounts
    +-- projets
    +-- equipes
    +-- documents
    +-- dashboard
    +-- jury
    +-- chatbot_ia
    +-- correction_ia
    |
    v
Base de données SQLite
    |
    v
Services IA Gemini
Base de données
La version actuelle du projet utilise SQLite afin de conserver les données de développement existantes.
Une migration vers PostgreSQL pourra être réalisée lors de la phase de finalisation et de déploiement.
Développement
Après chaque modification importante, vérifier le projet avec :
python manage.py check
Pour lancer le serveur :
python manage.py runserver
Auteur
Andriantsahala Arnaud M1 MIAGE SE20220175
Étudiant en Master 1 MIAGE — Informatique
Projet : Conception et réalisation d'une plateforme web de gestion des projets étudiants
