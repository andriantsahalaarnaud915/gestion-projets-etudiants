from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include


urlpatterns = [

    # ==================================================
    # ADMINISTRATION
    # ==================================================

    path(
        "admin/",
        admin.site.urls
    ),


    # ==================================================
    # AUTHENTIFICATION
    # ==================================================

    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html"
        ),
        name="login",
    ),

    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),


    # ==================================================
    # DASHBOARD
    # ==================================================

    path(
        "",
        include("dashboard.urls")
    ),


    # ==================================================
    # PROJETS
    # ==================================================

    path(
        "projets/",
        include("projets.urls")
    ),


    # ==================================================
    # DOCUMENTS
    # ==================================================

    path(
        "documents/",
        include("documents.urls")
    ),


    # ==================================================
    # CHATBOT IA
    # ==================================================

    path(
        "chatbot/",
        include("chatbot_ia.urls")
    ),


    # ==================================================
    # CORRECTION IA
    # ==================================================

    path(
        "correction-ia/",
        include("correction_ia.urls")
    ),


    # ==================================================
    # JURY / SOUTENANCES
    # ==================================================

    path(
        "jury/",
        include("jury.urls")
    ),
]


# ======================================================
# FICHIERS MEDIA
# ======================================================

urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT
)