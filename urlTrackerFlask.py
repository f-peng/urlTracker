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
    <title>URL Redirect Tracker</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f4f4;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 700px;
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
            padding: 10px;
            margin: 5px 0;
            border-radius: 4px;
            border: 1px solid #ccc;
            box-sizing: border-box;
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
        
	/* Source: https://codepo8.github.io/css-fork-on-github-ribbon */
        /* GitHub Fork Ribbon */
        #forkongithub a {
            background: #000;
            color: #fff;
            text-decoration: none;
            font-family: Arial, sans-serif;
            text-align: center;
            font-weight: bold;
            padding: 5px 40px;
            font-size: 1rem;
            line-height: 2rem;
            position: relative;
            transition: 0.5s;
        }
        #forkongithub a:hover {
            background: #3579f6;
            color: #fff;
        }
        #forkongithub a::before,
        #forkongithub a::after {
            content: "";
            width: 100%;
            display: block;
            position: absolute;
            top: 1px;
            left: 0;
            height: 1px;
            background: #fff;
        }
        #forkongithub a::after {
            bottom: 1px;
            top: auto;
        }
        @media screen and (min-width: 800px) {
            #forkongithub {
                position: absolute;
                display: block;
                top: 0;
                right: 0;
                width: 200px;
                overflow: hidden;
                height: 200px;
                z-index: 9999;
            }
            #forkongithub a {
                width: 200px;
                position: absolute;
                top: 60px;
                right: -60px;
                transform: rotate(45deg);
                -webkit-transform: rotate(45deg);
                -ms-transform: rotate(45deg);
                -moz-transform: rotate(45deg);
                -o-transform: rotate(45deg);
                box-shadow: 4px 4px 10px rgba(0, 0, 0, 0.8);
            }
        }
        /* Footer */
        footer {
            text-align: center;
            margin-top: 20px;
            padding-top: 10px;
            border-top: 1px solid #ccc;
            font-size: 0.9em;
        }
        footer a {
            text-decoration: none;
            color: #007bff;
        }
        footer span {
            margin: 0 5px;
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
    <!-- GitHub Fork Ribbon -->
    <span id="forkongithub"><a href="https://github.com/Secteur1">Fork me on GitHub</a></span>
    <!-- Footer -->
    <footer>
        Made with ❤️ <span>•</span> By <a href="https://github.com/f-peng">Frédéric</a>
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
