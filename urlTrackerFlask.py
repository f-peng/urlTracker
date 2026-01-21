from flask import Flask, request, render_template_string, flash, get_flashed_messages
import requests
import re

app = Flask(__name__)
app.secret_key = 'your_very_secure_secret_key'  # Changez ceci pour votre clé secrète réelle.

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

# Vérifie si l'URL est une adresse LAN
def is_lan_address(url):
    # Modèle de regex pour les adresses LAN
    lan_pattern = r'^(https?|ftp):\/\/(192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|10\.)(\d{1,3}\.\d{1,3})'
    return re.match(lan_pattern, url) is not None


@app.route('/', methods=['GET', 'POST'])
def trace_url():
    results = []
    start_url = ''  # Initialiser la variable pour l'URL de départ

    if request.method == 'POST':
        start_url = request.form.get('url')
        if start_url:
            # Vérifier si l'URL est une adresse LAN
            if is_lan_address(start_url):
                flash('Les adresses LAN ne sont pas autorisées.', 'error')
            else:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
                }
                session = requests.Session()
                session.headers.update(headers)

                try:
                    response = session.get(start_url, allow_redirects=True)
                    # On ne considère pas l'URL de départ comme une redirection
                    # Les redirections sont uniquement celles dans l'historique après la première
                    for resp in response.history[1:]:  # Commencer à partir du second élément de l'historique
                        results.append((resp.status_code, resp.url))
                    # Ajouter la réponse finale si elle est différente
                    if not response.history or response.history[-1].url != response.url:
                        results.append((response.status_code, response.url))
                except requests.RequestException as e:
                    flash(f"Erreur de suivi de l'URL : {e}", 'error')
        else:
            flash('Veuillez entrer une URL à tracer.', 'warning')

    return render_template_string(TEMPLATE, results=results, start_url=start_url)


if __name__ == '__main__':
    app.run(debug=True)
