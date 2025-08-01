# 🌟 Scraper Universel Fandom

## 🎬 Démo Vidéo

> **📹 Démo complète disponible** : [`Recording 2025-08-01 153606.mp4`](./Recording%202025-08-01%20153606.mp4)
> 
> *Cliquez sur le lien ci-dessus pour télécharger et voir la démonstration du scraper en action*

**Alternative** : Convertissez la vidéo en GIF animé pour un aperçu direct dans GitHub !

Application complète de scraping automatique pour les wikis **Fandom.com**, capable de s'adapter intelligemment aux différentes structures HTML et d'extraire des données de qualité depuis n'importe quel wiki Fandom.

**Composants** :
- **Backend** : Scraper Python avec détection automatique de catégories
- **Frontend** : Interface web avec recherche et comparateur
- **Validation** : Système de qualité automatique

## ✅ Fonctionnalités

### Exigences TP Réalisées
- [x] **Nom** - Extraction du titre principal
- [x] **Image principale** - URL complète et vérifiée (OBLIGATOIRE)
- [x] **Description/Biographie** - Contenu nettoyé
- [x] **Type/Rôle/Classe** - Extraction intelligente selon le contexte
- [x] **2+ attributs structurés** - Variables selon le fandom
- [x] **Interface front-end** avec cartes individuelles
- [x] **Barre de recherche** avec autocomplétion
- [x] **Comparateur** de personnages
- [x] **Gestion d'erreurs** robuste avec rapports

### 🎯 52 Fandoms Testés avec Succès

Le fichier `fandoms_a_tester.txt` contient **52 wikis Fandom fonctionnels** couvrant jeux vidéo, séries/films, animés/mangas, etc.

## 🚀 Fonctionnalités Bonus

### Détection Automatique de Catégories
Le scraper découvre automatiquement les meilleures catégories à scraper :
- Analyse de pertinence avec scoring
- Test de validation du contenu
- Fallback intelligent vers d'autres catégories

### Logique des 10 Fiches Minimum
Si moins de 10 fiches valides dans la catégorie principale :
1. Recherche automatique d'autres catégories  
2. Test de jusqu'à 5 alternatives
3. Sélection de la catégorie avec le plus de fiches
4. Rapport transparent de la catégorie utilisée

### Système de Qualité
- Validation en temps réel des données
- Nettoyage intelligent (références, contamination infobox)
- Score de qualité pour chaque fiche
- Rapports détaillés avec statistiques

## 🛠️ Structure du Projet

```
/scraper/           # Backend Python
  ├── app.py        # API Flask + logique scraping
  ├── data_cleaner.py   # Nettoyage et validation
  └── requirements.txt  # Dépendances

/frontend/          # Interface web
  ├── index.html    # Interface utilisateur
  ├── app.js        # Logique JavaScript
  └── style.css     # Styles modernes

/data/              # Données extraites (JSON + rapports)
test_runner.py      # Script de scraping de masse
fandoms_a_tester.txt    # 52 wikis validés
```

## 🚀 Installation et Utilisation

### Installation
```bash
cd scraper
pip install -r requirements.txt
```

### Lancement
```bash
# Démarrer le serveur
cd scraper
python app.py

# Interface web : http://localhost:5000
# 1. Entrer une URL Fandom (ex: https://starwars.fandom.com)
# 2. Cliquer "Lancer le Scraping"
# 3. Explorer avec recherche et comparateur
```

### Scraping de Masse
```bash
python test_runner.py
# Traite tous les fandoms dans fandoms_a_tester.txt
# Génère JSON et rapports dans /data/
```

## 📊 Résultats Obtenus

### 🎯 Performance Globale
- **Temps d'exécution** : 379.84 secondes (6 min 20s)
- **52 fandoms testés** avec 100% de succès
- **1,972 fiches extraites** au total
- **0 échec** de scraping
- **33,563 liens découverts** 
- **Moyenne** : 37.9 fiches par fandom

### 📈 Qualité des Données
- **100% des données** sont de qualité suffisante
- **Images valides** : Toutes les fiches incluent une image
- **Extraction moyenne** : 37.9 fiches par fandom (min: 10, max: 50)
- **Domaines couverts** : Jeux vidéo, séries/films, animés/mangas, littérature

### 🏆 Top Performers
- **Red Dead** : 50 fiches (100% succès)
- **Marvel Cinematic Universe** : 50 fiches (6,851 liens)
- **Breaking Bad** : 50 fiches (100% succès)
- **The Simpsons** : 49 fiches (5,486 liens)
- **Disney** : 48 fiches (9,894 liens)

**Défis résolus** :
- Structures HTML variables → Détection automatique
- Catégories multiples → Système de fallback intelligent
- Données contaminées → Pipeline de nettoyage avancé
- Images manquantes → Validation stricte avec fallback
