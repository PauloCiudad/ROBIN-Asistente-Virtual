import threading

import pytest
from PySide6.QtCore import QCoreApplication

from robin.ai.confirm import ConfirmationBroker, _accept_content, parse_yes_no

app = QCoreApplication.instance() or QCoreApplication([])


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Sí", True), ("sí, hazlo", True), ("Claro.", True), ("Dale", True), ("ok", True), ("De acuerdo", True),
        ("No", False), ("No, mejor no.", False), ("Cancela", False), ("espera", False),
        ("", None), ("¿Qué hora es?", None), ("mañana a las cinco", None),
    ],
)
def test_parse_yes_no(text, expected):
    assert parse_yes_no(text) is expected


def test_accept_content_simple_and_unknown_forms():
    assert _accept_content({"type": "object", "properties": {}}) == {}
    assert _accept_content({"properties": {"confirm": {"type": "boolean"}}}) == {"confirm": True}
    assert _accept_content({"properties": {"d": {"type": "string", "enum": ["deny", "approve"]}}}) == {"d": "approve"}
    # Texto libre obligatorio: ROBIN no inventa datos → se rechaza.
    assert _accept_content({"properties": {"to": {"type": "string"}}, "required": ["to"]}) is None


def _answer_later(broker: ConfirmationBroker, accepted: bool) -> None:
    def run():
        while not broker.pending:
            pass
        broker.resolve(accepted)
    threading.Thread(target=run, daemon=True).start()


def test_elicitation_accept_and_decline():
    broker = ConfirmationBroker()
    form = {"mode": "form", "message": "¿Crear evento?", "serverName": "Google Calendar",
            "requestedSchema": {"type": "object", "properties": {}}}
    _answer_later(broker, True)
    assert broker.handle_elicitation(form) == {"action": "accept", "content": {}}
    _answer_later(broker, False)
    assert broker.handle_elicitation(form) == {"action": "decline"}


def test_elicitation_times_out_as_decline():
    broker = ConfirmationBroker()
    assert broker.ask("¿Enviar correo?", timeout=0.1) is False


def test_unsupported_modes_are_declined():
    broker = ConfirmationBroker()
    assert broker.handle_elicitation({"mode": "openai/userVerification", "challenge": "x"}) == {"action": "decline"}
    assert broker.handle_elicitation({"mode": "url", "url": "http://inseguro"}) == {"action": "decline"}
