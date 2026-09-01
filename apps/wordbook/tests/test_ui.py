import pytest
from fastapi.testclient import TestClient
from wordbook.main import app
from wordbook.models import SourceError, WordNotFound
from wordbook.sources import PARSERS

DESKTOP_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
MOBILE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"


def _payload(word: str, language: str):
    if language == "es":
        return {
            "ok": True,
            "data": {
                "word": word,
                "meanings": [
                    {
                        "senses": [
                            {
                                "meaning_number": 1,
                                "category": "noun",
                                "gender": "masculine",
                                "description": f"definicion de {word}",
                                "examples": [f"ejemplo con {word}"],
                            }
                        ]
                    }
                ],
            },
        }
    return {
        "word": word,
        "entries": [
            {
                "partOfSpeech": "noun",
                "pronunciations": [{"type": "ipa", "text": "/x/", "tags": []}],
                "senses": [{"definition": f"definition of {word}", "examples": ["an example"]}],
            }
        ],
        "source": {"url": f"https://en.wiktionary.org/wiki/{word}"},
    }


@pytest.fixture
def client(monkeypatch):
    async def fake_lookup(language, word, *, client, settings):
        w = word.strip()
        if w.casefold() == "zzz":
            raise WordNotFound(w, ["zza", "zzb"])
        if w.casefold() == "boom":
            raise SourceError("down")
        raw = _payload(w, language)
        return PARSERS[language](raw, w), raw

    monkeypatch.setattr("wordbook.api.lookup", fake_lookup)
    with TestClient(app) as c:
        yield c


# ---- dual-UI contract --------------------------------------------------


def test_desktop_ua_redirects_to_d(client):
    r = client.get("/", headers={"user-agent": DESKTOP_UA}, follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/d/"


def test_mobile_ua_redirects_to_m(client):
    r = client.get("/", headers={"user-agent": MOBILE_UA}, follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/m/"


def test_pages_render(client):
    assert client.get("/d/").status_code == 200
    assert client.get("/m/").status_code == 200


def test_healthz(client):
    assert client.get("/healthz").json() == {"status": "ok"}


def test_static_assets(client):
    assert client.get("/static/style.css").status_code == 200
    assert client.get("/static/app.js").status_code == 200


def test_cross_links(client):
    assert "mobile site" in client.get("/d/").text.lower()
    assert "desktop site" in client.get("/m/").text.lower()


# ---- search ----------------------------------------------------------


def test_search_renders_blocks(client):
    r = client.get("/d/", params={"q": "casa", "lang": "es"})
    assert r.status_code == 200
    assert "definicion de casa" in r.text
    assert ">Save<" in r.text


def test_search_not_found_shows_suggestions(client):
    r = client.get("/d/", params={"q": "zzz", "lang": "es"})
    assert r.status_code == 200
    assert "No entry for" in r.text
    assert "zza" in r.text


def test_search_source_unavailable(client):
    r = client.get("/d/", params={"q": "boom", "lang": "en"})
    assert r.status_code == 200
    assert "respond" in r.text.lower()
    assert "boom" in r.text


def test_partial_result_is_a_fragment(client):
    r = client.get("/d/", params={"q": "casa", "lang": "es", "partial": "result"})
    assert r.status_code == 200
    assert "<html" not in r.text.lower()
    assert "definicion de casa" in r.text


def test_language_switch(client):
    assert 'data-lang="en"' in client.get("/d/", params={"lang": "en"}).text
    assert 'data-lang="es"' in client.get("/d/", params={"lang": "es"}).text


def test_bad_params_fall_back(client):
    r = client.get("/d/", params={"lang": "xx", "sort": "nope"})
    assert r.status_code == 200
    assert 'data-lang="es"' in r.text
    assert 'data-sort="alpha_asc"' in r.text


# ---- bookmark / remove (no-JS form path) --------------------------


def test_bookmark_then_remove_round_trip(client):
    r = client.post("/d/bookmark", data={"lang": "es", "word": "casa"}, follow_redirects=False)
    assert r.status_code == 303

    listing = client.get("/d/", params={"lang": "es"})
    assert 'class="saved"' in listing.text
    assert "casa" in listing.text

    r = client.post("/d/remove", data={"lang": "es", "word": "casa"}, follow_redirects=False)
    assert r.status_code == 303
    assert "casa" not in client.get("/d/", params={"lang": "es"}).text


def test_bookmark_reflected_in_result_card(client):
    client.post("/d/bookmark", data={"lang": "es", "word": "casa"})
    r = client.get("/d/", params={"q": "casa", "lang": "es"})
    assert ">Saved<" in r.text
