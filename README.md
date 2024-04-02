# EN

# URL Redirect Tracker Dockerized

`URL Redirect Tracker` is a simple web application developed using Flask, dockerized for easy installation and execution in any Docker environment.

## Features

- Tracking HTTP redirects from a specified URL;
- Displaying HTTP status codes and URLs for each redirect step;
- Prohibiting LAN addresses (192.168.*, 172.16.*, 10.*) for security reasons;
- Containerized with Docker for easy installation and execution.

## Prerequisites

Before getting started, make sure you have Docker installed on your system. You can download Docker from the official website: [Docker](https://www.docker.com/products/docker-desktop).

## Installation and Usage

1. Clone this repository to your local machine:
   ```
   git clone https://github.com/f-peng/urlTracker.git
   ```

2. Navigate to the project directory:
   ```
   cd urlTracker
   ```

3. Customize the configuration to your environment.

**Note regarding the secret key:**

Before deploying this application to production, please generate a strong and unique secret key to secure sessions and cookies. This secret key is used to sign cookies and prevent attacks such as cookie tampering or session attacks. A good practice is to use a random and complex string of characters. Here is an example of a secret key:

```
your_very_secure_secret_key
```

Make sure to replace this value with a unique and secure secret key before deploying the application to production. Keep this secret key confidential and do not share it with third parties.

4. Use docker-compose to build and run the Docker container:
   ```
   docker-compose up --build -d
   ```

6. Access the following URL in your web browser: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

6. Enter the URL you want to trace in the form and click the "Trace URL" button.

## Project Structure

- `Dockerfile`: Dockerfile to build the Docker image of the application;
- `docker-compose.yml`: docker-compose file to orchestrate the building and running of Docker containers;
- `urlTrackerFlask.py`: Main file of the Flask application;
- `requirements.txt`: Required Python dependencies.

## Todo

Implement a URL cleaning function (e.g., utm_*, etc.).

## Author

This project was developed by [Frd](https://github.com/f-peng).

## License

This project is licensed under the Apache License.

## Security

A `Bandit` scan has been performed, here is the report:

```
Run started:2024-04-02 13:34:38.525271

Test results:
>> Issue: [B105:hardcoded_password_string] Possible hardcoded password: 'your_very_secure_secret_key'
   Severity: Low   Confidence: Medium
   CWE: CWE-259 (https://cwe.mitre.org/data/definitions/259.html)
   More Info: https://bandit.readthedocs.io/en/1.7.8/plugins/b105_hardcoded_password_string.html
   Location: /code/urlTrackerFlask.py:6:17
5       app = Flask(__name__)
6       app.secret_key = 'your_very_secure_secret_key'  # Changez ceci pour votre clé secrète réelle.
7

--------------------------------------------------
>> Issue: [B201:flask_debug_true] A Flask app appears to be run with debug=True, which exposes the Werkzeug debugger and allows the execution of arbitrary code.
   Severity: High   Confidence: Medium
   CWE: CWE-94 (https://cwe.mitre.org/data/definitions/94.html)
   More Info: https://bandit.readthedocs.io/en/1.7.8/plugins/b201_flask_debug_true.html
   Location: /code/urlTrackerFlask.py:260:4
259     if __name__ == '__main__':
260         app.run(debug=True)

--------------------------------------------------

Code scanned:
        Total lines of code: 230
        Total lines skipped (#nosec): 0
        Total potential issues skipped due to specifically being disabled (e.g., #nosec BXXX): 0

Run metrics:
        Total issues (by severity):
                Undefined: 0
                Low: 1
                Medium: 0
                High: 1
        Total issues (by confidence):
                Undefined: 0
                Low: 0
                Medium: 2
                High: 0
Files skipped (0):
```

---

# FR

# Traceur des redirections d'URL Dockerisé

`URL Redirect Tracker` est une application Web simple développée en utilisant Flask, dockerisée pour une installation et une exécution faciles dans n'importe quel environnement Docker.

## Fonctionnalités

- Suivi des redirections HTTP à partir d'une URL spécifiée ;
- Affichage des codes de statut HTTP et des URL pour chaque étape de redirection ;
- Interdiction des adresses LAN (192.168.*, 172.16.*, 10.*) pour des raisons de sécurité ;
- Conteneurisé avec Docker pour une installation et une exécution faciles.

## Prérequis

Avant de commencer, assurez-vous d'avoir installé Docker sur votre système. Vous pouvez télécharger Docker à partir du site officiel : [Docker](https://www.docker.com/products/docker-desktop).

## Installation et Utilisation

1. Clonez ce dépôt sur votre machine locale :
   ```
   git clone https://github.com/f-peng/urlTracker.git
   ```

2. Accédez au répertoire du projet :
   ```
   cd urlTracker
   ```

3. Adapter la configuration à votre environnement.

**Note concernant la clé secrète :**

Avant de déployer cette application en production, veuillez générer une clé secrète forte et unique pour sécuriser les sessions et les cookies. Cette clé secrète est utilisée pour signer les cookies et prévenir les attaques telles que la falsification de cookies ou les attaques de session. Une bonne pratique consiste à utiliser une chaîne de caractères aléatoire et complexe. Voici un exemple de clé secrète : 

```
your_very_secure_secret_key
```

Assurez-vous de remplacer cette valeur par une clé secrète unique et sécurisée avant de déployer l'application en production. Gardez cette clé secrète confidentielle et ne la partagez pas avec des tiers.

4. Utilisez docker-compose pour construire et exécuter le conteneur Docker :
   ```
   docker-compose up --build -d
   ```

6. Accédez à l'URL suivante dans votre navigateur Web : [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

6. Entrez l'URL que vous souhaitez tracer dans le formulaire et cliquez sur le bouton "Trace URL".

## Structure du Projet

- `Dockerfile`: Fichier Dockerfile pour construire l'image Docker de l'application ;
- `docker-compose.yml`: Fichier docker-compose pour orchestrer la construction et l'exécution des conteneurs Docker ;
- `urlTrackerFlask.py`: Fichier principal de l'application Flask ;
- `requirements.txt` : Les dépendances Python prérequises.

## Todo

Mettre en place une fonction de nettoyage des URL (eg. utm_*, etc.).

## Auteur

Ce projet a été développé par [Frd](https://github.com/f-peng).

## Licence

Ce projet est sous licence Apache.

## Sécurité

Un scan `Bandit` a été effectué dont voici le rapport :

```
Run started:2024-04-02 13:34:38.525271

Test results:
>> Issue: [B105:hardcoded_password_string] Possible hardcoded password: 'your_very_secure_secret_key'
   Severity: Low   Confidence: Medium
   CWE: CWE-259 (https://cwe.mitre.org/data/definitions/259.html)
   More Info: https://bandit.readthedocs.io/en/1.7.8/plugins/b105_hardcoded_password_string.html
   Location: /code/urlTrackerFlask.py:6:17
5       app = Flask(__name__)
6       app.secret_key = 'your_very_secure_secret_key'  # Changez ceci pour votre clé secrète réelle.
7

--------------------------------------------------
>> Issue: [B201:flask_debug_true] A Flask app appears to be run with debug=True, which exposes the Werkzeug debugger and allows the execution of arbitrary code.
   Severity: High   Confidence: Medium
   CWE: CWE-94 (https://cwe.mitre.org/data/definitions/94.html)
   More Info: https://bandit.readthedocs.io/en/1.7.8/plugins/b201_flask_debug_true.html
   Location: /code/urlTrackerFlask.py:260:4
259     if __name__ == '__main__':
260         app.run(debug=True)

--------------------------------------------------

Code scanned:
        Total lines of code: 230
        Total lines skipped (#nosec): 0
        Total potential issues skipped due to specifically being disabled (e.g., #nosec BXXX): 0

Run metrics:
        Total issues (by severity):
                Undefined: 0
                Low: 1
                Medium: 0
                High: 1
        Total issues (by confidence):
                Undefined: 0
                Low: 0
                Medium: 2
                High: 0
Files skipped (0):
```

[![security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)