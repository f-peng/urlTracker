import socket

import pytest
import responses

import urlTrackerFlask as app_module
from urlTrackerFlask import TraceError, app, check_url, trace

PUBLIC = '93.184.215.14'


@pytest.fixture
def dns(monkeypatch):
    """Résolution simulée : {nom: [adresses]} ; un nom absent est introuvable."""
    table = {}

    def fake_getaddrinfo(host, port, *args, **kwargs):
        if host not in table:
            raise socket.gaierror('introuvable')
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


@responses.activate
def test_chaine_de_redirections(dns):
    dns['a.test'] = dns['b.test'] = [PUBLIC]
    responses.get('http://a.test/', status=301, headers={'Location': 'https://b.test/x'})
    responses.get('https://b.test/x', status=302, headers={'Location': '/fin'})
    responses.get('https://b.test/fin', status=200)
    assert trace('http://a.test/') == [
        (301, 'http://a.test/'), (302, 'https://b.test/x'), (200, 'https://b.test/fin')]


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
def test_page_affiche_les_etapes(dns):
    dns['a.test'] = [PUBLIC]
    responses.get('http://a.test/', status=301, headers={'Location': 'http://a.test/b'})
    responses.get('http://a.test/b', status=200)
    page = app.test_client().post('/', data={'url': 'http://a.test/'}).get_data(as_text=True)
    assert '<span class="url">http://a.test/b</span>' in page
    assert '>200</span>' in page and '>301</span>' not in page  # l'URL de départ n'est pas répétée


def test_page_refuse_interne(dns):
    dns['localhost'] = ['127.0.0.1']
    page = app.test_client().post('/', data={'url': 'http://localhost/'}).get_data(as_text=True)
    assert 'Les adresses internes ne sont pas autoris' in page
