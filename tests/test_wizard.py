from types import SimpleNamespace

import pytest

from core.wizard import WizardDefinition, WizardManager, WizardStep


async def noop(update, context, data):
    return None


async def async_noop(*args, **kwargs):
    return None


def make_update(text="", query=None):
    message = SimpleNamespace(reply_text=async_noop, text=text)
    return SimpleNamespace(message=message, effective_message=message, callback_query=query)


@pytest.mark.asyncio
async def test_start_creates_session():
    definition = WizardDefinition(name="demo", steps=[WizardStep("name", "Nom ?")], summary=lambda data: str(data), on_confirm=noop)
    manager = WizardManager({"demo": definition})
    context = SimpleNamespace(user_data={})
    await manager.start(make_update(), context, "demo")
    assert manager.active(context)
    assert context.user_data["_yessal_wizard"]["name"] == "demo"


@pytest.mark.asyncio
async def test_text_advances_and_stores_value():
    definition = WizardDefinition(name="demo", steps=[WizardStep("name", "Nom ?"), WizardStep("phone", "Téléphone ?")], summary=lambda data: str(data), on_confirm=noop)
    manager = WizardManager({"demo": definition})
    context = SimpleNamespace(user_data={})
    await manager.start(make_update(), context, "demo")
    update = make_update("TEST")
    assert await manager.handle_text(update, context)
    session = context.user_data["_yessal_wizard"]
    assert session["data"]["name"] == "TEST"
    assert session["step_index"] == 1


@pytest.mark.asyncio
async def test_edit_text_returns_to_summary_without_advancing():
    summaries = []
    async def capture_summary(*args, **kwargs):
        summaries.append(True)
    definition = WizardDefinition(name="demo", steps=[WizardStep("name", "Nom ?"), WizardStep("phone", "Téléphone ?")], summary=lambda data: str(data), on_confirm=noop)
    manager = WizardManager({"demo": definition})
    context = SimpleNamespace(user_data={"_yessal_wizard": {"name":"demo","step_index":1,"data":{"name":"A","phone":"111"},"editing":"phone"}})
    update = make_update("222")
    await manager.handle_text(update, context)
    session=context.user_data["_yessal_wizard"]
    assert session["data"]["phone"] == "222"
    assert session["step_index"] == 1
    assert session["editing"] is None


@pytest.mark.asyncio
async def test_cancel_word_clears_session():
    definition = WizardDefinition(name="demo", steps=[WizardStep("name", "Nom ?")], summary=lambda data: str(data), on_confirm=noop)
    manager = WizardManager({"demo": definition})
    context = SimpleNamespace(user_data={"_yessal_wizard":{"name":"demo","step_index":0,"data":{}}})
    await manager.handle_text(make_update("ECHAP"), context)
    assert not manager.active(context)


@pytest.mark.asyncio
async def test_previous_and_next_navigation():
    definition = WizardDefinition(name="demo", steps=[WizardStep("a", "A ?"), WizardStep("b", "B ?"), WizardStep("c", "C ?")], summary=lambda data: str(data), on_confirm=noop)
    manager = WizardManager({"demo": definition})
    context = SimpleNamespace(user_data={"_yessal_wizard":{"name":"demo","step_index":1,"data":{"a":"A","b":"B"}}})
    qprev=SimpleNamespace(data="wiz:prev", answer=async_noop, edit_message_text=async_noop)
    await manager.handle_callback(make_update(query=qprev), context)
    assert context.user_data["_yessal_wizard"]["step_index"] == 0
    qnext=SimpleNamespace(data="wiz:next", answer=async_noop, edit_message_text=async_noop)
    await manager.handle_callback(make_update(query=qnext), context)
    assert context.user_data["_yessal_wizard"]["step_index"] == 1


@pytest.mark.asyncio
async def test_parser_error_does_not_advance():
    def parse_phone(value):
        if not value.isdigit():
            raise ValueError("Téléphone invalide.")
        return value
    definition = WizardDefinition(name="demo", steps=[WizardStep("phone", "Téléphone ?", parser=parse_phone)], summary=lambda data: str(data), on_confirm=noop)
    manager = WizardManager({"demo": definition})
    context = SimpleNamespace(user_data={})
    await manager.start(make_update(), context, "demo")
    await manager.handle_text(make_update("abc"), context)
    session = context.user_data["_yessal_wizard"]
    assert session["step_index"] == 0
    assert "phone" not in session["data"]


def test_clear_removes_session():
    manager = WizardManager({})
    context = SimpleNamespace(user_data={"_yessal_wizard": {"name": "demo"}})
    manager.clear(context)
    assert not manager.active(context)


@pytest.mark.asyncio
async def test_stale_callback_session_is_handled():
    answered = []
    async def answer(*args, **kwargs): answered.append((args, kwargs))
    query = SimpleNamespace(data="wiz:cancel", answer=answer, edit_message_text=async_noop)
    update = SimpleNamespace(callback_query=query)
    context = SimpleNamespace(user_data={})
    manager = WizardManager({})
    assert await manager.handle_callback(update, context)
    assert answered
    assert answered[0][1]["show_alert"] is True
