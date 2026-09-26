from flask import Flask, request, render_template_string, flash, get_flashed_messages
import requests
import ipaddress
import os
import secrets
import socket
import time
from urllib.parse import urljoin, urlsplit

app = Flask(__name__)
# Sans SECRET_KEY, une clé aléatoire par processus suffit : les messages flash sont lus dans la même requête.
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}
ALLOWED_PORTS = {'http': 80, 'https': 443}
MAX_REDIRECTS = 10
TIMEOUT = (5, 10)  # connexion, lecture
DEADLINE = 25  # secondes pour toute la chaîne, sous le timeout de 30 s de gunicorn

TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>URL Redirect Tracker</title>
    <style>
        *, *::before, *::after {
            box-sizing: border-box;
        }
        html {
            overflow-x: hidden;
        }
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f4f4;
            margin: 0;
            padding: 10px;
            overflow-x: hidden;
        }
        .container {
            max-width: 700px;
            width: 100%;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        .header {
            background-color: #007bff;
            color: white;
            padding: 10px 15px;
            text-align: center;
        }
        .trace-form input[type="text"], .trace-form button {
            width: 100%;
            padding: 12px;
            margin: 5px 0;
            border-radius: 4px;
            border: 1px solid #ccc;
            box-sizing: border-box;
            font-size: 16px;
        }
        .trace-form button {
            background-color: #007bff;
            color: white;
            border: none;
            cursor: pointer;
        }
        .trace-form button:hover {
            background-color: #0056b3;
        }

        .start-url {
            background-color: #fff3cd; /* Un jaune plus doux pour le statut 'Start' */
            color: #856404;  /* Une couleur de texte plus douce pour une meilleure lisibilité */
            border: 1px solid #ffeeba;  /* Une bordure légère pour mettre en valeur sans choquer */
            margin: 10px 0;
            padding: 10px;
            overflow-wrap: break-word;
        }

        .redirection, .final-url {
            background-color: #e9e9e9;
            border: 1px solid #ddd;
            margin: 10px 0;
            padding: 10px;
            overflow-wrap: break-word;
        }
        .final-url {
            background-color: #4CAF50; /* Vert pour le statut 200 */
            color: white;
        }

        .status-code {
            font-size: 0.9em;  /* Réduction de la taille de police */
            font-weight: bold;
            padding: 2px 6px;  /* Réduction de l'espacement autour du texte */
            border-radius: 4px;  /* Bordures arrondies */
            display: inline-block;  /* Utiliser display inline-block pour une meilleure disposition */
            margin-right: 5px;  /* Espace à droite du badge */
        }

        .status-start {
            background-color: #FFD700; /* Jaune pour le statut 'Start' */
        }
        .status-302 {
            background-color: #2196F3; /* Bleu pour les redirections 302 */
        }
        .status-200 {
            background-color: #dff0d8; /* Un vert plus clair pour le fond */
            color: #3c763d; /* Du vert foncé pour le texte */
            border-color: #d6e9c6; /* Une bordure plus claire pour la boîte */
        }
        .arrow {
            color: #2196F3;
            display: block;
            font-size: 1.5em;
        }
        
        /* Footer */
        footer {
            text-align: center;
            margin-top: 30px;
            padding: 20px 10px;
            border-top: 1px solid #e0e0e0;
            font-size: 0.9em;
            color: #666;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 10px;
        }
        footer a {
            text-decoration: none;
            color: #666;
            transition: color 0.3s ease;
        }
        footer a:hover {
            color: #007bff;
        }
        .footer-separator {
            width: 60px;
            height: 1px;
            background-color: #ddd;
            margin: 5px 0;
        }
        
        @media screen and (max-width: 576px) {
            body {
                padding: 5px;
            }
            .container {
                padding: 15px;
            }
            .header h2 {
                font-size: 1.5em;
            }
            .status-code {
                font-size: 0.8em;
                padding: 2px 4px;
            }
            .start-url, .redirection, .final-url {
                padding: 8px;
                margin: 8px 0;
            }
            .arrow {
                font-size: 1.2em;
            }
            footer {
                font-size: 0.8em;
                padding: 15px 10px;
                gap: 8px;
            }
            .footer-separator {
                width: 40px;
            }
        }
        
        @media screen and (min-width: 577px) and (max-width: 768px) {
            body {
                padding: 15px;
            }
            .container {
                padding: 18px;
            }
        }
        
        @media screen and (min-width: 1200px) {
            .container {
                max-width: 900px;
            }
        }
    </style>


</head>
<body>
    <div class="container">
        <div class="header">
            <h2>URL Redirect Tracker</h2>
        </div>
        <div class="trace-form">
            <form method="post">
                <input type="text" name="url" placeholder="Enter the URL">
                <button type="submit">Trace URL</button>
            </form>
        </div>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        {% if start_url %}
        <div class="start-url">
            <span class="status-code status-start">Start</span>
            <span class="url">{{ start_url }}</span>
        </div>
        {% endif %}
        {% for status, url in results %}
        <div class="{% if status == 200 %}final-url{% else %}redirection{% endif %}">
            <span class="status-code {% if status == 200 %}status-200{% else %}status-302{% endif %}">{{ status }}</span>
            <span class="url">{{ url }}</span>
        </div>
        {% endfor %}
    </div>
    <!-- Footer -->
    <footer>
        Made with ❤️ by <a href="https://github.com/f-peng">Frédéric</a>
        <div class="footer-separator"></div>
        <a href="https://github.com/f-peng/urlTracker">github.com/f-peng/urlTracker</a>
    </footer>
</body>
</html>
'''

class TraceError(Exception):
    """Suivi refusé ou interrompu ; le message est affiché tel quel."""


def check_url(url):
    """Refuse toute URL qui ne mène pas, en http(s) sur le port standard, à une adresse publique.

    Le nom est résolu et chacune de ses adresses est vérifiée : cela couvre localhost, les
    réseaux privés, link-local, CGNAT, et les noms internes (services du cluster, par exemple).
    """
    parts = urlsplit(url)
    if parts.scheme not in ALLOWED_PORTS:
        raise TraceError('Seules les URL http et https sont acceptées.')
    try:
        port = parts.port
    except ValueError:
        raise TraceError('URL invalide.')
    if not parts.hostname:
        raise TraceError('URL invalide.')
    if port not in (None, ALLOWED_PORTS[parts.scheme]):
        raise TraceError('Seuls les ports 80 et 443 sont acceptés.')
    try:
        infos = socket.getaddrinfo(parts.hostname, port or ALLOWED_PORTS[parts.scheme], type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError):
        raise TraceError(f'Nom de domaine introuvable : {parts.hostname}')
    for *_, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0].split('%')[0])
        if ip.version == 6 and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        if not ip.is_global:
            raise TraceError('Les adresses internes ne sont pas autorisées.')


def trace(start_url):
    """Suit les redirections une à une, en vérifiant chaque étape ; renvoie [(statut, url), …]."""
    session = requests.Session()
    session.trust_env = False  # pas de proxy ni de .netrc venant de l'environnement
    session.headers.update(HEADERS)
    deadline = time.monotonic() + DEADLINE
    hops = []
    url = start_url
    for _ in range(MAX_REDIRECTS + 1):
        if time.monotonic() > deadline:
            raise TraceError('Délai dépassé.')
        check_url(url)
        # stream : seuls le statut et les en-têtes comptent, le corps n'est pas téléchargé
        with session.get(url, allow_redirects=False, timeout=TIMEOUT, stream=True) as resp:
            hops.append((resp.status_code, resp.url))
            if not resp.is_redirect:
                return hops
            url = urljoin(resp.url, resp.headers['Location'])
    raise TraceError(f'Plus de {MAX_REDIRECTS} redirections.')


@app.route('/', methods=['GET', 'POST'])
def trace_url():
    results = []
    start_url = ''  # Initialiser la variable pour l'URL de départ

    if request.method == 'POST':
        start_url = request.form.get('url', '').strip()
        if start_url:
            try:
                hops = trace(start_url)
                # L'URL de départ est affichée à part : on ne la répète que s'il n'y a pas eu de redirection
                results = hops[1:] or hops
            except TraceError as e:
                flash(str(e), 'error')
            except requests.RequestException as e:
                flash(f"Erreur de suivi de l'URL : {e}", 'error')
        else:
            flash('Veuillez entrer une URL à tracer.', 'warning')

    return render_template_string(TEMPLATE, results=results, start_url=start_url)


if __name__ == '__main__':
    app.run()
