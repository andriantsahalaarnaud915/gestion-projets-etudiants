from pathlib import Path

from pypdf import PdfReader
from docx import Document as DocxDocument


def extraire_texte_pdf(chemin):
    reader = PdfReader(chemin)

    texte = []

    for page in reader.pages:
        contenu = page.extract_text()

        if contenu:
            texte.append(contenu)

    return "\n".join(texte)


def extraire_texte_docx(chemin):
    document = DocxDocument(chemin)

    paragraphes = []

    for paragraphe in document.paragraphs:
        if paragraphe.text.strip():
            paragraphes.append(paragraphe.text)

    return "\n".join(paragraphes)


def extraire_texte_document(document):
    chemin = document.fichier.path

    extension = Path(chemin).suffix.lower()

    if extension == ".pdf":
        return extraire_texte_pdf(chemin)

    elif extension == ".docx":
        return extraire_texte_docx(chemin)

    else:
        raise ValueError(
            "Format non supporté. Utilisez un fichier PDF ou DOCX."
        )