"""
Fichier de lancement unique (livrable obligatoire #2 du sujet).
Lance l'API FastAPI ET ouvre le dashboard Streamlit.

Usage : python run.py
"""
import subprocess
import sys
import time
import webbrowser


def main():
    print("Démarrage de l'API FastAPI sur http://localhost:8000 ...")
    api_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"]
    )
    time.sleep(2)

    print("Démarrage du dashboard Streamlit sur http://localhost:8501 ...")
    demo_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "demo/streamlit_app.py"]
    )

    print("\n--- mAIntenance & Assistance ---")
    print("API docs      : http://localhost:8000/docs")
    print("Démo + dashboard : http://localhost:8501")
    print("Ctrl+C pour arrêter les deux services.\n")

    try:
        api_process.wait()
        demo_process.wait()
    except KeyboardInterrupt:
        api_process.terminate()
        demo_process.terminate()


if __name__ == "__main__":
    main()
