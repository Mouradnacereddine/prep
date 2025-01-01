# Backend Django REST API

## Structure
```
backend/
├── config/         # Configuration Django
├── gestion_prep/   # Application principale
├── user_auth/      # Gestion des utilisateurs
├── preparateur/    # Module préparateur
└── requirements/   # Dépendances Python
    ├── base.txt    # Dépendances principales
    ├── local.txt   # Outils de développement
    └── production.txt # Configuration production
```

## Installation

### Développement
```bash
# Créer l'environnement virtuel
python -m venv venv
source venv/Scripts/activate  # Windows

# Installer les dépendances de développement
pip install -r requirements/local.txt

# Migrations
python manage.py migrate

# Créer un superutilisateur (admin)
python manage.py createsuperuser
# Suivez les instructions pour créer votre compte admin :
# 1. Entrez une adresse email
# 2. Entrez un mot de passe sécurisé
# 3. Confirmez le mot de passe

# Lancer le serveur de développement
python manage.py runserver
```

### Production
```bash
python -m venv venv
source venv/Scripts/activate  # Windows

# Installer les dépendances de production
pip install -r requirements/production.txt

# Migrations
python manage.py migrate

# Créer un superutilisateur (admin)
python manage.py createsuperuser

# Lancer avec gunicorn
gunicorn config.wsgi:application
```

## Administration Django
Après avoir créé un superutilisateur, vous pouvez accéder à l'interface d'administration :
1. Allez sur http://localhost:8000/admin/
2. Connectez-vous avec l'email et le mot de passe de votre superutilisateur

## API Endpoints

### Authentication
- `POST /api/auth/register/` - Inscription
- `POST /api/auth/login/` - Connexion
- `POST /api/auth/logout/` - Déconnexion
- `POST /api/auth/token/refresh/` - Rafraîchir le token

### Utilisateurs
- `GET /api/users/me/` - Profil utilisateur
- `PUT /api/auth/profile/update/` - Mise à jour du profil
- `POST /api/auth/password/change/` - Changement de mot de passe

### Département
- `GET /api/auth/department/users/` - Liste des utilisateurs du département
- `GET /api/auth/department/stats/` - Statistiques du département

## Tests
```bash
# Installation des dépendances de développement nécessaires
pip install -r requirements/local.txt

# Lancer les tests
python manage.py test
```

## Linting et Formatage
```bash
# Les outils sont inclus dans requirements/local.txt
black .
flake8
