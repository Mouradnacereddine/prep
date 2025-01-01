# Projet de Préparation (Prep)

## Description
Application de gestion de préparation avec une architecture full-stack utilisant Django (backend) et Next.js (frontend).

## Structure du Projet
```
prep/
├── backend/         # API Django REST
│   └── requirements/# Fichiers de dépendances Python
├── frontend/        # Application Next.js
└── certs/          # Certificats SSL
```

## Prérequis
- Python 3.8+
- Node.js 16+
- npm ou yarn
- Virtualenv

## Installation

### Backend (Django)
```bash
cd backend
python -m venv venv
source venv/Scripts/activate  # Windows

# Pour le développement
pip install -r requirements/local.txt

# Pour la production
# pip install -r requirements/production.txt

python manage.py migrate
python manage.py runserver
```

### Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev
```

## Configuration
1. Créer un fichier `.env` dans le dossier backend en suivant `.env.example`
2. Créer un fichier `.env.local` dans le dossier frontend en suivant `.env.example`

## Développement
- Backend API: http://localhost:8000
- Frontend: http://localhost:3005
- Admin Django: http://localhost:8000/admin/

## Structure des Requirements
Le backend utilise trois fichiers de requirements :
- `requirements/base.txt` : Dépendances principales
- `requirements/local.txt` : Outils de développement
- `requirements/production.txt` : Dépendances de production

## Licence
Propriétaire - Tous droits réservés
