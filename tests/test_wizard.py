from types import SimpleNamespace

import pytest

from core.wizard import WizardDefinition, WizardManager, WizardStep


async def noop(update, context, data):
    return None


@pytest.mark.asyncio
async def test_start_creates_session():
    definition = WizardDefinition(
        name="demo",
        steps=[WizardStep("name", "Nom ?")],
        summary=lambda data: str(data),
        on_confirm=noop,
    )
    manager = WizardManager({"demo": definition})
    context = SimpleNamespace(user_data={})
    message = SimpleNamespace(reply_text=async_noop, text="")
    update = SimpleNamespace(
        message=message,
        effective_message=message,
        callback_query=None,
    )

    await manager.start(update, context, "demo")

    assert manager.active(context)
    assert context.user_data["_yessal_wizard"]["name"] == "demo"


@pytest.mark.asyncio
async def test_text_advances_and_stores_value():
    definition = WizardDefinition(
        name="demo",
        steps=[
            WizardStep("name", "Nom ?"),
            WizardStep("phone", "Téléphone ?"),
        ],
        summary=lambda data: str(data),
        on_confirm=noop,
    )
    manager = WizardManager({"demo": definition})
    context = SimpleNamespace(user_data={})
    message = SimpleNamespace(reply_text=async_noop, text="TEST")
    update = SimpleNamespace(
        message=message,
        effective_message=message,
        callback_query=None,
    )

    await manager.start(update, context, "demo")
    assert await manager.handle_text(update, context)

    session = context.user_data["_yessal_wizard"]
    assert session["data"]["name"] == "TEST"
    assert session["step_index"] == 1


@pytest.mark.asyncio
async def test_parser_error_does_not_advance():
    def parse_phone(value):
        if not value.isdigit():
            raise ValueError("Téléphone invalide.")
        return value

    definition = WizardDefinition(
        name="demo",
        steps=[WizardStep("phone", "Téléphone ?", parser=parse_phone)],
        summary=lambda data: str(data),
        on_confirm=noop,
    )
    manager = WizardManager({"demo": definition})
    context = SimpleNamespace(user_data={})
    message = SimpleNamespace(reply_text=async_noop, text="abc")
    update = SimpleNamespace(
        message=message,
        effective_message=message,
        callback_query=None,
    )

    await manager.start(update, context, "demo")
    await manager.handle_text(update, context)

    session = context.user_data["_yessal_wizard"]
    assert session["step_index"] == 0
    assert "phone" not in session["data"]


def test_clear_removes_session():
    manager = WizardManager({})
    context = SimpleNamespace(
        user_data={"_yessal_wizard": {"name": "demo"}}
    )
    manager.clear(context)
    assert not manager.active(context)


async def async_noop(*args, **kwargs):
    return None


@pytest.mark.asyncio
async def test_stale_callback_session_is_handled():
    answered = []

    async def answer(*args, **kwargs):
        answered.append((args, kwargs))

    query = SimpleNamespace(
        data="wiz:cancel",
        answer=answer,
        edit_message_text=async_noop,
    )
    update = SimpleNamespace(callback_query=query)
    context = SimpleNamespace(user_data={})
    manager = WizardManager({})

    assert await manager.handle_callback(update, context)
    assert answered
    assert answered[0][1]["show_alert"] is True
