#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  SETUP.SH — Installation de l'environnement Python du projet
# ─────────────────────────────────────────────────────────────
#
# QU'EST-CE QU'UN VENV ?
# ─────────────────────
# Un "venv" (environnement virtuel) est un dossier isolé
# qui contient sa propre version de Python et ses propres
# librairies. Sans venv, toutes tes librairies s'installent
# "globalement" sur le Pi, ce qui peut créer des conflits
# entre projets (ex: projet A a besoin de FastAPI v0.100,
# projet B a besoin de FastAPI v0.115 → impossible sans venv).
#
# Avec un venv : chaque projet a son propre espace isolé.
# C'est la bonne pratique universelle en Python.
#
# COMMENT UTILISER CE SCRIPT ?
# ────────────────────────────
# 1. Copie ce fichier dans le dossier /api/ de ton projet
# 2. Rends-le exécutable : chmod +x setup.sh
# 3. Lance-le : ./setup.sh
# ─────────────────────────────────────────────────────────────

set -e  # Arrête le script immédiatement si une commande échoue

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Pi Web — Installation de l'environnement"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


# ── ÉTAPE 1 : Vérifier Python ─────────────────
echo ""
echo "▶ Vérification de Python..."
python3 --version
# On s'assure que Python 3 est bien disponible sur le Pi.
# Si cette commande échoue, Python n'est pas installé.


# ── ÉTAPE 2 : Créer le venv ───────────────────
echo ""
echo "▶ Création de l'environnement virtuel..."

# Le dossier "venv" sera créé dans le même dossier que ce script.
# "python3 -m venv" = utilise le module venv intégré à Python
# pour créer un environnement isolé dans le dossier ./venv/
python3 -m venv venv

echo "   ✓ Environnement virtuel créé dans ./venv/"


# ── ÉTAPE 3 : Activer le venv ─────────────────
echo ""
echo "▶ Activation de l'environnement virtuel..."

# "source" = exécute le script d'activation dans le shell courant.
# Après ça, la commande "python" et "pip" pointeront vers
# les versions isolées dans ./venv/ et non vers le Python global.
source venv/bin/activate

echo "   ✓ Environnement virtuel actif"


# ── ÉTAPE 4 : Mettre à jour pip ───────────────
echo ""
echo "▶ Mise à jour de pip..."
# pip est le gestionnaire de paquets Python.
# On le met à jour pour éviter les avertissements
# et s'assurer qu'il peut lire les formats modernes.
pip install --upgrade pip --quiet

echo "   ✓ pip à jour"


# ── ÉTAPE 5 : Installer les dépendances ───────
echo ""
echo "▶ Installation des dépendances depuis requirements.txt..."
# "-r requirements.txt" = lit le fichier et installe tout
# "--quiet" = réduit le volume des logs dans le terminal
pip install -r requirements.txt --quiet

echo "   ✓ Toutes les dépendances installées"


# ── ÉTAPE 6 : Vérifier le fichier .env ────────
echo ""
echo "▶ Vérification du fichier .env..."

if [ ! -f ".env" ]; then
    # Si le fichier .env n'existe pas, on en crée un vide
    # avec les clés nécessaires pour rappeler à l'utilisateur
    # de les remplir.
    echo "   ⚠ Fichier .env introuvable — création d'un modèle vide..."
    cat > .env << 'EOF'
# ─── SECRETS DU PROJET PI WEB ───────────────
# Remplace les valeurs vides par tes vraies valeurs.
# Ce fichier ne doit JAMAIS être commité sur GitHub
# (il est déjà dans .gitignore).

# Clé secrète pour signer les JWT.
# Génère une valeur forte avec : python3 -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=

# Mot de passe de l'application Gmail pour l'envoi d'emails.
# À générer dans les paramètres Google > Sécurité > Mots de passe d'application.
SMTP_PASSWORD=

# Clé API DeepL (free tier) pour traduire les synopsis.
# À obtenir sur : https://www.deepl.com/fr/pro-api
DEEPL_API_KEY=
EOF
    echo "   ✓ Fichier .env créé — remplis les valeurs avant de lancer le serveur"
else
    echo "   ✓ Fichier .env trouvé"
fi


# ── RÉSUMÉ FINAL ──────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Installation terminée !"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Pour démarrer le serveur :"
echo "  1. Active le venv  : source venv/bin/activate"
echo "  2. Lance le serveur: uvicorn main:app --host 0.0.0.0 --port 3333 --reload"
echo ""
echo "⚠ Pense à remplir le fichier .env avant de lancer !"
echo ""