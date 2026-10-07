import socket

import pytest
import responses

import urlTrackerFlask as app_module
from urlTrackerFlask import TraceError, app, check_url, clean_url, trace

PUBLIC = '93.184.215.14'


@pytest.fixture
def dns(monkeypatch):
    """Résolution simulée : {nom: [adresses]} ; un nom absent est introuvable."""
    table = {}

    def fake_getaddrinfo(host, port, *args, **kwargs):
        if table.get(host) == 'again':
            raise socket.gaierror(socket.EAI_AGAIN, 'temporary failure')
        if host not in table:
            raise socket.gaierror(socket.EAI_NONAME, 'introuvable')
        return [(socket.AF_INET6 if ':' in a else socket.AF_INET, socket.SOCK_STREAM, 6, '', (a, port))
                for a in table[host]]

    monkeypatch.setattr(app_module.socket, 'getaddrinfo', fake_getaddrinfo)
    return table


@pytest.mark.parametrize('address', [
    '127.0.0.1', '10.43.0.1', '10.42.0.58', '172.16.0.1', '192.168.228.249',
    '169.254.169.254', '100.64.0.1', '0.0.0.0', '::1', 'fd00::1', 'fe80::1', '::ffff:127.0.0.1',
])
def test_adresses_internes_refusees(dns, address):
    dns['cible.test'] = [address]
    with pytest.raises(TraceError, match='internes'):
        check_url('http://cible.test/')


def test_une_seule_adresse_interne_suffit(dns):
    dns['mixte.test'] = [PUBLIC, '10.0.0.1']
    with pytest.raises(TraceError):
        check_url('https://mixte.test/')


def test_adresse_ip_litterale(dns):
    dns['127.0.0.1'] = ['127.0.0.1']
    with pytest.raises(TraceError):
        check_url('http://127.0.0.1/')


@pytest.mark.parametrize('url', ['ftp://example.test/', 'file:///etc/passwd', 'gopher://x/', 'example.test'])
def test_schemas_refuses(dns, url):
    with pytest.raises(TraceError, match='http'):
        check_url(url)


@pytest.mark.parametrize('url', ['http://example.test:8080/', 'https://example.test:80/', 'http://example.test:99999/'])
def test_ports_refuses(dns, url):
    dns['example.test'] = [PUBLIC]
    with pytest.raises(TraceError):
        check_url(url)


def test_nom_introuvable(dns):
    with pytest.raises(TraceError, match='introuvable'):
        check_url('http://miniflux/')


def test_url_publique_acceptee(dns):
    dns['example.test'] = [PUBLIC]
    check_url('https://example.test/')
    check_url('http://example.test:80/')


def test_dns_indisponible_distinct_de_introuvable(dns):
    dns['lent.test'] = 'again'
    with pytest.raises(TraceError, match='indisponible'):
        check_url('http://lent.test/')


@responses.activate
def test_chaine_de_redirections(dns):
    dns['a.test'] = dns['b.test'] = [PUBLIC]
    responses.get('http://a.test/', status=301, headers={'Location': 'https://b.test/x'})
    responses.get('https://b.test/x', status=302, headers={'Location': '/fin'})
    responses.get('https://b.test/fin', status=200)
    hops = trace('http://a.test/')
    assert [(h['status'], h['url']) for h in hops] == [
        (301, 'http://a.test/'), (302, 'https://b.test/x'), (200, 'https://b.test/fin')]


@responses.activate
def test_details_de_chaque_etape(dns):
    dns['a.test'] = [PUBLIC, '2606:2800:220:1:248:1893:25c8:1946']
    responses.get('http://a.test/', status=301, headers={
        'Location': 'https://a.test/fin', 'Server': 'nginx', 'Set-Cookie': 'sid=secret; Path=/'})
    responses.get('https://a.test/fin', status=200, content_type='text/html', body='<p>fin</p>')
    first, last = trace('http://a.test/')
    assert first['reason'] == 'Moved Permanently' and 'permanente' in first['meaning']
    assert first['host'] == 'a.test' and first['ips'] == [PUBLIC, '2606:2800:220:1:248:1893:25c8:1946']
    assert first['server'] == 'nginx' and first['location'] == 'https://a.test/fin'
    assert first['cookies'] == ['sid'] and first['kind'] == 'http' and isinstance(first['ms'], int)
    assert last['kind'] is None and last['reason'] == 'OK'


@responses.activate
def test_meta_refresh_suivi(dns):
    dns['a.test'] = [PUBLIC]
    responses.get('http://a.test/', status=200, content_type='text/html; charset=utf-8',
                  body='<html><head><META HTTP-EQUIV="Refresh" CONTENT="0; URL=\'/suite\'"></head></html>')
    responses.get('http://a.test/suite', status=200, content_type='text/html', body='<p>fin</p>')
    first, last = trace('http://a.test/')
    assert first['kind'] == 'meta' and 'meta refresh' in first['note']
    assert last['url'] == 'http://a.test/suite'


@responses.activate
def test_meta_refresh_vers_interne_bloque(dns):
    dns['a.test'] = [PUBLIC]
    dns['metadata.test'] = ['169.254.169.254']
    responses.get('http://a.test/', status=200, content_type='text/html',
                  body='<meta http-equiv="refresh" content="0;url=http://metadata.test/">')
    with pytest.raises(TraceError, match='internes') as e:
        trace('http://a.test/')
    assert len(e.value.hops) == 1 and len(responses.calls) == 1


@responses.activate
def test_redirection_javascript_signalee_pas_suivie(dns):
    dns['a.test'] = [PUBLIC]
    responses.get('http://a.test/', status=200, content_type='text/html',
                  body='<script>window.location.href = "http://a.test/js"</script>')
    (hop,) = trace('http://a.test/')
    assert 'JavaScript' in hop['note'] and len(responses.calls) == 1


@responses.activate
def test_page_non_html_non_lue(dns):
    dns['a.test'] = [PUBLIC]
    responses.get('http://a.test/', status=200, content_type='application/json',
                  body='<meta http-equiv="refresh" content="0;url=/x">')
    assert len(trace('http://a.test/')) == 1


@responses.activate
def test_redirection_vers_interne_bloquee(dns):
    dns['a.test'] = [PUBLIC]
    dns['metadata.test'] = ['169.254.169.254']
    responses.get('http://a.test/', status=302, headers={'Location': 'http://metadata.test/latest'})
    with pytest.raises(TraceError, match='internes'):
        trace('http://a.test/')
    assert len(responses.calls) == 1  # la cible interne n'est jamais contactée


@responses.activate
def test_boucle_de_redirections(dns):
    dns['a.test'] = [PUBLIC]
    responses.get('http://a.test/', status=302, headers={'Location': 'http://a.test/'})
    with pytest.raises(TraceError, match='redirections'):
        trace('http://a.test/')


@responses.activate
def test_echec_conserve_les_etapes_parcourues(dns):
    dns['a.test'] = [PUBLIC]  # b.test n'existe pas
    responses.get('http://a.test/', status=302, headers={'Location': 'http://b.test/x'})
    with pytest.raises(TraceError, match='introuvable: b.test|introuvable : b.test') as e:
        trace('http://a.test/')
    assert [h['status'] for h in e.value.hops] == [302] and e.value.url == 'http://b.test/x'


@responses.activate
def test_page_affiche_les_etapes(dns):
    dns['a.test'] = [PUBLIC]
    responses.get('http://a.test/', status=301, headers={'Location': 'http://a.test/b'})
    responses.get('http://a.test/b', status=200)
    page = app.test_client().post('/', data={'url': 'http://a.test/'}).get_data(as_text=True)
    assert '<div class="url">http://a.test/</div>' in page  # l'URL de départ est la première étape
    assert '<div class="url">http://a.test/b</div>' in page
    assert 'Moved Permanently' in page and '2 étapes' in page and '1 redirection' in page


@responses.activate
def test_page_echec_au_milieu_de_la_chaine(dns):
    dns['a.test'] = [PUBLIC]
    responses.get('http://a.test/', status=302, headers={'Location': 'http://tracker.test/x'})
    page = app.test_client().post('/', data={'url': 'http://a.test/'}).get_data(as_text=True)
    assert '<strong>Found</strong>' in page  # l'étape réussie reste affichée
    assert 'Nom de domaine introuvable : tracker.test' in page
    assert '<div class="url">http://tracker.test/x</div>' in page


def test_page_refuse_interne(dns):
    dns['localhost'] = ['127.0.0.1']
    page = app.test_client().post('/', data={'url': 'http://localhost/'}).get_data(as_text=True)
    assert 'Les adresses internes ne sont pas autoris' in page


def test_page_url_vide(dns):
    page = app.test_client().post('/', data={'url': ' '}).get_data(as_text=True)
    assert 'Veuillez entrer une URL' in page


def test_nettoyage_retire_les_parametres_de_suivi():
    url = ('https://www.coursera.org/google-certificates/google-ai?irclickid=xRf&irgwc=1&afsrc=1&utm_medium=partners'
           '&UTM_Source=impact&cuid=ppr-fr-1&=&lang=fr#plans')
    cleaned, removed = clean_url(url)
    assert cleaned == 'https://www.coursera.org/google-certificates/google-ai?lang=fr#plans'
    assert removed == ['irclickid', 'irgwc', 'afsrc', 'utm_medium', 'UTM_Source', 'cuid', '(sans nom)']


@pytest.mark.parametrize('url', [
    'https://a.test/', 'https://a.test/p?id=3&q=a%20b&page=2', 'https://a.test/?key=abc&ref=x'])
def test_nettoyage_ne_touche_pas_au_reste(url):
    assert clean_url(url) == (url, [])


def test_nettoyage_supprime_le_point_d_interrogation_vide():
    assert clean_url('https://a.test/p?utm_source=x&fbclid=y') == ('https://a.test/p', ['utm_source', 'fbclid'])


@responses.activate
def test_page_option_nettoyage(dns):
    dns['a.test'] = [PUBLIC]
    responses.get('http://a.test/', status=301, headers={'Location': 'http://a.test/b?utm_source=x&id=7'})
    responses.get('http://a.test/b?utm_source=x&id=7', status=200)
    client = app.test_client()
    sans = client.post('/', data={'url': 'http://a.test/'}).get_data(as_text=True)
    avec = client.post('/', data={'url': 'http://a.test/', 'clean': '1'}).get_data(as_text=True)
    assert 'URL finale nettoyée' not in sans and 'name="clean" value="1" >' in sans
    assert '<div class="url">http://a.test/b?id=7</div>' in avec and 'Paramètres retirés : utm_source' in avec
    assert 'value="1" checked>' in avec
