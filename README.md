# Panel Free Fire

Une application Flask pour gérer les joueurs Free Fire.

## Déploiement sur Vercel

### Prérequis
- Un compte Vercel (https://vercel.com)
- Git installé sur votre machine

### Étapes de déploiement

1. **Initialiser un repository Git** (si ce n'est pas déjà fait):
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   ```

2. **Pousser vers GitHub** (optionnel mais recommandé):
   - Créez un nouveau repository sur GitHub
   - Ajoutez l'origine remote:
     ```bash
     git remote add origin https://github.com/votre-username/votre-repo.git
     git branch -M main
     git push -u origin main
     ```

3. **Déployer sur Vercel**:
   
   **Option A: Via le site web Vercel**
   - Allez sur https://vercel.com
   - Connectez-vous avec votre compte GitHub
   - Cliquez sur "New Project"
   - Importez votre repository
   - Vercel détectera automatiquement la configuration

   **Option B: Via Vercel CLI**
   ```bash
   npm i -g vercel
   vercel login
   vercel --prod
   ```

### Configuration

L'application utilise les fichiers suivants pour le déploiement:
- `vercel.json` - Configuration Vercel
- `requirements.txt` - Dépendances Python
- `api/index.py` - Point d'entrée de l'application

### Variables d'environnement

Vous pouvez configurer les variables d'environnement suivantes dans Vercel:
- `SECRET_KEY` - Clé secrète pour Flask (recommandé en production)

### Structure du projet

```
.
├── api/
│   └── index.py          # Application Flask principale
├── templates/            # Templates HTML
├── vercel.json          # Configuration Vercel
├── requirements.txt     # Dépendances Python
└── README.md           # Ce fichier
```

### Notes importantes

- Les données utilisateur sont stockées dans `/tmp/` sur Vercel (temporaire)
- Pour une solution de stockage persistant, considérez l'utilisation d'une base de données externe
- L'application est configurée pour fonctionner en mode serverless sur Vercel
