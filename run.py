"""
Fichier de lancement unique (livrable obligatoire #2 du sujet).
Lance uniquement l'API FastAPI — le frontend (NestJS) est un projet séparé
qui consomme cette API (voir README.md pour les endpoints /chat et /ticket).

Usage : python run.py
"""
import os
import sys

import uvicorn


def main():
    port = int(os.environ.get("PORT", 8000))
    print(f"Démarrage de l'API FastAPI sur http://localhost:{port} ...")
    print(f"Docs interactives      : http://localhost:{port}/docs")
    print(f"Endpoint conversationnel (frontend) : POST http://localhost:{port}/chat")
    print("Ctrl+C pour arrêter.\n")

    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
