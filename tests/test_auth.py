from ntulearn_downloader.auth import resolve_cookie


def test_resolve_cookie_prefers_process_environment(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("NTULEARN_COOKIE=expires:dotenv\n")
    monkeypatch.setenv("NTULEARN_COOKIE", "expires:process")
    monkeypatch.setattr(
        "ntulearn_downloader.auth.read_bbrouter_cookie",
        lambda: "expires:browser",
    )

    assert resolve_cookie() == "expires:process"


def test_resolve_cookie_loads_dotenv_before_browser(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NTULEARN_COOKIE", "")
    (tmp_path / ".env").write_text("NTULEARN_COOKIE=expires:dotenv\n")
    monkeypatch.setattr(
        "ntulearn_downloader.auth.read_bbrouter_cookie",
        lambda: "expires:browser",
    )

    assert resolve_cookie() == "expires:dotenv"


def test_resolve_cookie_falls_back_to_browser_without_environment(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("NTULEARN_COOKIE", raising=False)
    monkeypatch.setattr(
        "ntulearn_downloader.auth.read_bbrouter_cookie",
        lambda: "expires:browser",
    )

    assert resolve_cookie() == "expires:browser"
