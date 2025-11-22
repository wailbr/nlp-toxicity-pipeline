 README — Test Technique : Pipeline d’Analyse de Toxicité
Auteur : Brimesse Ouail
Date : Octobre 2025

    Objectif du projet
Ce projet met en place un pipeline complet de traitement de données textuelles, depuis la collecte d’articles sur plusieurs sites d’actualité jusqu’à leur analyse automatique de toxicité et leur visualisation, le tout déployé avec Docker.

    Structure du projet
Test_Technique_Brimesse_Ouail/
│
├── rapport_word/
│   └── Rendu_Test_Technique.docx
│
├── presentation/
│   └── Rendu_Test_Technique.pptx
│
├── code_source/
│   ├── scraper.py
│   ├── api.py
│   ├── analyze_stats.py
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── requirements.txt
│
├── images/
│   ├── capture_scraping.png
│   ├── capture_graph.png
│   ├── capture_docker.png
│   └── ...
│
└── README.txt



   Instructions d’exécution

1️-Installation locale (optionnelle)
pip install -r requirements.txt
python scraper.py
uvicorn api:app --reload
python analyze_stats.py

2️-Exécution via Docker
docker compose up --build
L’application FastAPI sera accessible sur http://localhost:8000

     Description rapide des fichiers
- scraper.py → extraction des articles depuis 7 sites d’actualité (BeautifulSoup + Selenium)
- api.py → API FastAPI de prédiction NLP (modèle sentiment-analysis)
- analyze_stats.py → calcul et visualisation des taux de toxicité + stockage dans MongoDB
- Dockerfile / docker-compose.yml → conteneurisation et orchestration du projet
- rapport_word / présentation → livrables finaux (documentation et slides du projet)

   Technologies principales
- Python 3.11
- BeautifulSoup, Selenium
- FastAPI
- Transformers (Hugging Face)
- Pandas, Seaborn, Matplotlib
- MongoDB
- Docker & Docker Compose

   Résumé
Ce projet illustre les différentes étapes d’un pipeline ETL appliqué à du texte :
- Extract : collecte des articles
- Transform : nettoyage + prédiction NLP
- Load : stockage et visualisation

Un exemple concret d’ingénierie de données textuelles appliquée à la détection de toxicité.
