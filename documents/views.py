from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from projets.models import Projet
from .models import Document

@login_required
def deposer_document(request, projet_id):
    projet = get_object_or_404(Projet, pk=projet_id)
    
    if request.method == "POST":
        titre = request.POST.get("titre")
        type_document = request.POST.get("type_document")
        fichier = request.FILES.get("fichier")
        
        if fichier:
            Document.objects.create(
                titre=titre,
                fichier=fichier,
                type_document=type_document,
                projet=projet,
                depose_par=request.user
            )
            messages.success(request, "Document déposé avec succès !")
            return redirect("detail_projet", pk=projet.pk)
    
    return render(request, "documents/deposer.html", {"projet": projet})