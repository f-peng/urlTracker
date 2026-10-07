from flask import Flask, request, render_template_string, flash, get_flashed_messages
import requests
import ipaddress
import os
import re
import secrets
import socket
import time
from html.parser import HTMLParser
from http import HTTPStatus
from urllib.parse import urljoin, urlsplit
from urllib3.exceptions import HTTPError as Urllib3Error

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
BODY_LIMIT = 65536  # octets lus d'une page 200 pour y chercher une redirection <meta refresh>
BODY_MIN_TIME = 5  # pas de lecture du corps s'il reste moins de secondes avant l'échéance

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

        .summary {
            margin: 15px 0 5px;
            color: #555;
            font-size: 0.95em;
        }
        .hop {
            border: 1px solid #ddd;
            border-left: 5px solid #2196F3;
            background-color: #fafafa;
            margin: 10px 0;
            padding: 10px;
            overflow-wrap: anywhere;
        }
        .hop.ok { border-left-color: #4CAF50; background-color: #f1f8f1; }
        .hop.meta { border-left-color: #ff9800; }
        .hop.err { border-left-color: #dc3545; background-color: #fdf0f0; }
        .hop .head { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px; }
        .hop .num { color: #888; font-size: 0.85em; }
        .hop .url { font-family: monospace; font-size: 0.95em; }
        .hop .url b { color: #000; }
        .hop .meaning { margin: 4px 0 0; font-size: 0.9em; color: #555; }
        .hop dl {
            display: grid;
            grid-template-columns: max-content 1fr;
            gap: 2px 12px;
            margin: 8px 0 0;
            font-size: 0.85em;
        }
        .hop dt { color: #777; }
        .hop dd { margin: 0; overflow-wrap: anywhere; }
        .hop dd.mono { font-family: monospace; }
        .note { margin: 6px 0 0; font-size: 0.85em; color: #8a5a00; }
        .status-code {
            font-size: 0.9em;
            font-weight: bold;
            padding: 2px 6px;
            border-radius: 4px;
            display: inline-block;
            color: white;
            background-color: #2196F3; /* 3xx */
        }
        .status-2 { background-color: #4CAF50; }
        .status-meta { background-color: #ff9800; }
        .status-4, .status-5, .status-err { background-color: #dc3545; }
        .alert { padding: 10px; margin: 10px 0; border-radius: 4px; background-color: #fff3cd; color: #856404; }
        .alert-error { background-color: #f8d7da; color: #721c24; }

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
            .hop {
                padding: 8px;
                margin: 8px 0;
            }
            .hop dl {
                grid-template-columns: 1fr;
                gap: 0;
            }
            .hop dd { margin-bottom: 4px; }
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
        {% if hops %}
        <p class="summary">
            {{ hops | length }} étape{{ 's' if hops | length > 1 }}
            · {{ redirections }} redirection{{ 's' if redirections > 1 }}
            · {{ total_ms }} ms
        </p>
        {% endif %}
        {% for hop in hops %}
        <div class="hop {{ 'ok' if hop.status < 300 else ('meta' if hop.kind == 'meta' else '') }}">
            <div class="head">
                <span class="num">#{{ hop.n }}</span>
                <span class="status-code status-{{ hop.status // 100 }}">{{ hop.status }}</span>
                <strong>{{ hop.reason }}</strong>
            </div>
            <div class="url">{{ hop.url }}</div>
            <p class="meaning">{{ hop.meaning }}</p>
            <dl>
                <dt>Domaine</dt><dd>{{ hop.host }}</dd>
                {% if hop.ips %}<dt>Adresse IP</dt><dd class="mono">{{ hop.ips | join(', ') }}</dd>{% endif %}
                <dt>Temps de réponse</dt><dd>{{ hop.ms }} ms</dd>
                {% if hop.server %}<dt>Serveur</dt><dd>{{ hop.server }}</dd>{% endif %}
                {% if hop.content_type %}<dt>Type de contenu</dt><dd>{{ hop.content_type }}</dd>{% endif %}
                {% if hop.location %}<dt>En-tête Location</dt><dd class="mono">{{ hop.location }}</dd>{% endif %}
                {% if hop.refresh %}<dt>Balise meta refresh</dt><dd class="mono">{{ hop.refresh }}</dd>{% endif %}
                {% if hop.cookies %}<dt>Cookies déposés</dt><dd>{{ hop.cookies | join(', ') }}</dd>{% endif %}
            </dl>
            {% if hop.note %}<p class="note">{{ hop.note }}</p>{% endif %}
        </div>
        {% endfor %}
        {% if failure %}
        <div class="hop err">
            <div class="head">
                <span class="num">#{{ hops | length + 1 }}</span>
                <span class="status-code status-err">Échec</span>
            </div>
            {% if failure_url %}<div class="url">{{ failure_url }}</div>{% endif %}
            <p class="meaning">{{ failure }}</p>
        </div>
        {% endif %}
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
    """Suivi refusé ou interrompu ; le message est affiché tel quel.

    `hops` : les étapes déjà parcourues ; `url` : l'adresse sur laquelle le suivi s'est arrêté.
    """
    def __init__(self, message, hops=None, url=None):
        super().__init__(message)
        self.hops = hops or []
        self.url = url


MEANINGS = {
    200: 'La page existe : fin de la chaîne.',
    301: 'Redirection permanente : les moteurs de recherche retiennent la nouvelle adresse.',
    302: 'Redirection temporaire (« Found »).',
    303: 'Redirection temporaire : la suite se lit en GET (« See Other »).',
    307: 'Redirection temporaire, méthode HTTP conservée.',
    308: 'Redirection permanente, méthode HTTP conservée.',
}


def meaning(status):
    if status in MEANINGS:
        return MEANINGS[status]
    if 200 <= status < 300:
        return 'Succès : fin de la chaîne.'
    if 300 <= status < 400:
        return 'Redirection.'
    if 400 <= status < 500:
        return 'Erreur côté client : la page est introuvable ou refusée.'
    if status >= 500:
        return 'Erreur côté serveur.'
    return ''


def check_url(url):
    """Refuse toute URL qui ne mène pas, en http(s) sur le port standard, à une adresse publique.

    Le nom est résolu et chacune de ses adresses est vérifiée : cela couvre localhost, les
    réseaux privés, link-local, CGNAT, et les noms internes (services du cluster, par exemple).
    Renvoie les adresses résolues, sans doublon.
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
    except socket.gaierror as e:
        if e.errno == socket.EAI_AGAIN:
            raise TraceError(f'Résolution DNS indisponible pour {parts.hostname} : réessayez dans un instant.')
        raise TraceError(f'Nom de domaine introuvable : {parts.hostname}')
    except UnicodeError:
        raise TraceError(f'Nom de domaine introuvable : {parts.hostname}')
    addresses = []
    for *_, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0].split('%')[0])
        if ip.version == 6 and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        if not ip.is_global:
            raise TraceError('Les adresses internes ne sont pas autorisées.')
        if str(ip) not in addresses:
            addresses.append(str(ip))
    return addresses


class _MetaRefresh(HTMLParser):
    """Cherche <meta http-equiv="refresh" content="N; url=…"> dans le début d'une page."""
    def __init__(self):
        super().__init__()
        self.target = self.content = None

    def handle_starttag(self, tag, attrs):
        if tag != 'meta' or self.target:
            return
        attrs = dict(attrs)
        if (attrs.get('http-equiv') or '').lower() != 'refresh':
            return
        content = attrs.get('content') or ''
        m = re.match(r'\s*\d+(?:\.\d+)?\s*[;,]?\s*(?:url\s*=\s*)?[\'"]?([^\'"]+)', content, re.I)
        if m and m.group(1).strip():
            self.target, self.content = m.group(1).strip(), content


JS_REDIRECT = re.compile(
    r'(?:location(?:\.href)?\s*=|location\.(?:replace|assign)\()\s*[\'"]([^\'"]+)[\'"]', re.I)


def read_redirect_in_body(resp, hop):
    """Cherche une redirection dans une page 200 : <meta refresh> (suivie) ou JavaScript (signalée seulement).

    Renvoie l'adresse suivante, ou None.
    """
    if 'html' not in (resp.headers.get('Content-Type') or '').lower():
        return None
    try:
        body = resp.raw.read(BODY_LIMIT, decode_content=True).decode('utf-8', 'replace')
    except (OSError, Urllib3Error):
        return None
    parser = _MetaRefresh()
    try:
        parser.feed(body)
    except Exception:  # HTML invalide : on n'en tire simplement rien
        pass
    if parser.target:
        hop['kind'] = 'meta'
        hop['refresh'] = parser.content
        hop['note'] = 'Redirection côté page (balise meta refresh), suivie.'
        return parser.target
    m = JS_REDIRECT.search(body)
    if m:
        hop['note'] = f'Redirection JavaScript possible vers {m.group(1)} (non suivie : exécuter du code n\'est pas fait ici).'
    return None


def describe(resp, number, addresses, elapsed):
    try:
        reason = HTTPStatus(resp.status_code).phrase
    except ValueError:
        reason = resp.reason or ''
    return {
        'n': number,
        'status': resp.status_code,
        'reason': reason,
        'meaning': meaning(resp.status_code),
        'url': resp.url,
        'host': urlsplit(resp.url).hostname,
        'ips': addresses,
        'ms': round(elapsed * 1000),
        'server': resp.headers.get('Server'),
        'content_type': resp.headers.get('Content-Type'),
        'location': resp.headers.get('Location'),
        # noms seulement : les valeurs des cookies n'ont rien à faire dans la page
        'cookies': [c.split('=', 1)[0].strip() for c in resp.raw.headers.getlist('Set-Cookie')],
        'kind': 'http' if resp.is_redirect else None,
        'refresh': None,
        'note': None,
    }


def trace(start_url):
    """Suit les redirections une à une, en vérifiant chaque étape ; renvoie la liste des étapes (dicts).

    En cas d'échec, TraceError porte les étapes déjà parcourues et l'adresse en cause.
    """
    session = requests.Session()
    session.trust_env = False  # pas de proxy ni de .netrc venant de l'environnement
    session.headers.update(HEADERS)
    deadline = time.monotonic() + DEADLINE
    hops = []
    url = start_url
    try:
        for _ in range(MAX_REDIRECTS + 1):
            if time.monotonic() > deadline:
                raise TraceError('Délai dépassé.')
            addresses = check_url(url)
            started = time.monotonic()
            # stream : seuls le statut et les en-têtes comptent, le corps n'est lu que pour un <meta refresh>
            with session.get(url, allow_redirects=False, timeout=TIMEOUT, stream=True) as resp:
                hop = describe(resp, len(hops) + 1, addresses, time.monotonic() - started)
                hops.append(hop)
                if resp.is_redirect:
                    url = urljoin(resp.url, resp.headers['Location'])
                    continue
                if resp.status_code != 200 or deadline - time.monotonic() < BODY_MIN_TIME:
                    return hops
                target = read_redirect_in_body(resp, hop)
                if not target:
                    return hops
                url = urljoin(resp.url, target)
        raise TraceError(f'Plus de {MAX_REDIRECTS} redirections.')
    except TraceError as e:
        e.hops, e.url = hops, e.url or url
        raise
    except requests.RequestException as e:
        raise TraceError(f"Erreur de suivi de l'URL : {e}", hops, url) from e


@app.route('/', methods=['GET', 'POST'])
def trace_url():
    hops, failure, failure_url = [], None, None

    if request.method == 'POST':
        start_url = request.form.get('url', '').strip()
        if start_url:
            try:
                hops = trace(start_url)
            except TraceError as e:
                hops, failure, failure_url = e.hops, str(e), e.url
        else:
            flash('Veuillez entrer une URL à tracer.', 'warning')

    return render_template_string(
        TEMPLATE, hops=hops, failure=failure, failure_url=failure_url,
        redirections=sum(1 for h in hops if h['kind']), total_ms=sum(h['ms'] for h in hops))


if __name__ == '__main__':
    app.run()
