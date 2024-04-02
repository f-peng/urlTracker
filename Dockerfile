# Utiliser une image de base Python Alpine pour minimiser la taille de l'image
FROM python:3.9-alpine

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Installer les dépendances nécessaires pour compiler certaines des dépendances Python
# Puis installez Gunicorn avec pip
COPY requirements.txt /app/
RUN apk add --no-cache build-base linux-headers \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install gunicorn

# Copier le reste des fichiers de l'application dans le conteneur
COPY urlTrackerFlask.py /app

# Exposer le port sur lequel Gunicorn va s'exécuter
EXPOSE 8000

# Exécuter l'application avec Gunicorn
CMD ["gunicorn", "--access-logfile", "-", "--error-logfile", "-", "-b", "0.0.0.0:8000", "urlTrackerFlask:app"]
