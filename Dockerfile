# Étape de construction : dépendances dans un venv sans pip
FROM python:3.13-alpine AS build
COPY requirements.txt /tmp/
RUN python -m venv --without-pip /venv \
    && pip --python /venv/bin/python install --no-cache-dir -r /tmp/requirements.txt

# Image finale : paquets Alpine à jour, sans pip (ses dépendances embarquées ressortent au scan)
FROM python:3.13-alpine
RUN apk upgrade --no-cache \
    && pip uninstall -y pip
COPY --from=build /venv /venv
WORKDIR /app
COPY urlTrackerFlask.py .
ENV PATH=/venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1
USER 10001:10001
EXPOSE 8000
# Système de fichiers en lecture seule : battements des workers dans /dev/shm, pas de socket de contrôle
CMD ["gunicorn", "--access-logfile", "-", "--error-logfile", "-", "--worker-tmp-dir", "/dev/shm", "--no-control-socket", "-b", "0.0.0.0:8000", "urlTrackerFlask:app"]
