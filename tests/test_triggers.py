import triggers


def setup_trigger_config(monkeypatch):
    monkeypatch.setattr(triggers, "nickname", "Terminator")


def test_detect_prefix_trigger(monkeypatch):
    setup_trigger_config(monkeypatch)

    triggered, content = triggers.extract_trigger_content("Terminator: explique isso")

    assert triggered is True
    assert content == "explique isso"


def test_detect_prefix_trigger_case_insensitive(monkeypatch):
    setup_trigger_config(monkeypatch)

    triggered, content = triggers.extract_trigger_content("terminator: explique isso")

    assert triggered is True
    assert content == "explique isso"


def test_detect_suffix_question_trigger(monkeypatch):
    setup_trigger_config(monkeypatch)

    triggered, content = triggers.extract_trigger_content("como funciona isso Terminator?")

    assert triggered is True
    assert content == "como funciona isso"


def test_detect_command_trigger(monkeypatch):
    setup_trigger_config(monkeypatch)

    triggered, content = triggers.extract_trigger_content("!status")

    assert triggered is True
    assert content == "!status"


def test_ignore_normal_message(monkeypatch):
    setup_trigger_config(monkeypatch)

    triggered, content = triggers.extract_trigger_content("mensagem comum de canal")

    assert triggered is False
    assert content is None
