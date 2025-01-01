# Frontend Next.js

## Description
Interface utilisateur moderne pour l'application de gestion de préparation, construite avec Next.js 14 et TypeScript.

## Prérequis
- Node.js 16+
- npm ou yarn
- Backend Django en cours d'exécution

## Installation

```bash
# Installer les dépendances
npm install

# Lancer en développement
npm run dev

# Build pour production
npm run build

# Lancer en production
npm start
```

## Configuration
Créer un fichier `.env.local` avec les variables suivantes :
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SITE_URL=http://localhost:3005
```

## Structure du Projet
```
frontend/
├── app/            # Pages et composants (App Router)
├── components/     # Composants réutilisables
├── contexts/       # Contextes React
├── public/         # Fichiers statiques
└── tests/          # Tests
```

## Scripts Disponibles
- `npm run dev` - Mode développement
- `npm run build` - Build production
- `npm start` - Lancer en production
- `npm run lint` - Vérification ESLint
- `npm test` - Lancer les tests

## Développement
- URL de développement : http://localhost:3005
- Hot reloading activé
- ESLint et TypeScript pour la qualité du code

## Tests
```bash
# Lancer les tests
npm test

# Couverture des tests
npm run test:coverage
```

## Plus d'Informations
- [Documentation Next.js](https://nextjs.org/docs)
- [App Router](https://nextjs.org/docs/app)
- [Optimisations](https://nextjs.org/docs/app/building-your-application/optimizing)
