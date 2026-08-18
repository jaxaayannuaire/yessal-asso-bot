"""Generic conversational Wizard engine for Yessal Asso Bot."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

Parser = Callable[[str], Any]
AsyncCallback = Callable[[Update, ContextTypes.DEFAULT_TYPE, dict[str, Any]], Awaitable[None]]
KeyboardFactory = Callable[[dict[str, Any]], Optional[InlineKeyboardMarkup]]
SummaryFactory = Callable[[dict[str, Any]], str]


@dataclass
class WizardStep:
    key: str
    prompt: str
    parser: Parser = lambda value: value.strip()
    keyboard: Optional[KeyboardFactory] = None
    required: bool = True


@dataclass
class WizardDefinition:
    name: str
    steps: list[WizardStep]
    summary: SummaryFactory
    on_confirm: AsyncCallback
    title: str = ""
    allow_edit: bool = True


@dataclass
class WizardSession:
    name: str
    step_index: int = 0
    data: dict[str, Any] = field(default_factory=dict)
    editing: Optional[str] = None


class WizardManager:
    """Reusable state machine shared by all conversational workflows."""

    SESSION_KEY = "_yessal_wizard"
    CALLBACK_PREFIX = "wiz:"
    CANCEL_WORDS = frozenset({"echap", "esc", "escape", "annuler", "cancel"})

    def __init__(self, definitions: dict[str, WizardDefinition]):
        self.definitions = definitions

    def active(self, context) -> bool:
        return bool(context.user_data.get(self.SESSION_KEY))

    def session(self, context) -> Optional[WizardSession]:
        raw = context.user_data.get(self.SESSION_KEY)
        if not raw:
            return None
        return WizardSession(
            name=raw["name"],
            step_index=raw.get("step_index", 0),
            data=dict(raw.get("data", {})),
            editing=raw.get("editing"),
        )

    def _save(self, context, session: WizardSession) -> None:
        context.user_data[self.SESSION_KEY] = {
            "name": session.name,
            "step_index": session.step_index,
            "data": session.data,
            "editing": session.editing,
        }

    def clear(self, context) -> None:
        context.user_data.pop(self.SESSION_KEY, None)

    async def start(self, update, context, name: str, initial=None):
        definition = self.definitions[name]
        session = WizardSession(name=name, data=dict(initial or {}))
        self._save(context, session)
        await self._render_step(update, context, definition, session)

    async def handle_text(self, update, context) -> bool:
        session = self.session(context)
        if not session:
            return False

        definition = self.definitions.get(session.name)
        if not definition:
            self.clear(context)
            return False

        text = (update.message.text or "").strip()
        if text.casefold() in self.CANCEL_WORDS:
            self.clear(context)
            await update.message.reply_text("❌ Opération annulée.")
            return True

        step = definition.steps[session.step_index]

        if step.required and not text:
            await update.message.reply_text("❌ Cette information est obligatoire.")
            return True

        try:
            value = step.parser(text)
        except ValueError as exc:
            await update.message.reply_text(f"❌ {exc}")
            await self._render_step(update, context, definition, session)
            return True

        if step.required and value in (None, ""):
            await update.message.reply_text("❌ Cette information est obligatoire.")
            return True

        session.data[step.key] = value

        # En mode édition, une saisie valide termine l'édition et revient
        # immédiatement au récapitulatif. Elle ne doit jamais avancer à l'étape suivante.
        if session.editing:
            session.editing = None
            self._save(context, session)
            await self._render_summary(update, context, definition, session)
            return True

        session.step_index += 1
        self._save(context, session)

        if session.step_index >= len(definition.steps):
            await self._render_summary(update, context, definition, session)
        else:
            await self._render_step(update, context, definition, session)
        return True

    async def handle_callback(self, update, context) -> bool:
        query = update.callback_query
        if not query:
            return False

        session = self.session(context)
        if not session:
            await query.answer("Cette session Wizard n'est plus active.", show_alert=True)
            return True

        payload = query.data or ""
        if not payload.startswith(self.CALLBACK_PREFIX):
            return False

        await query.answer()
        definition = self.definitions.get(session.name)

        if not definition:
            self.clear(context)
            await query.edit_message_text("❌ Assistant indisponible.")
            return True

        parts = payload.split(":", 3)
        action = parts[1] if len(parts) > 1 else ""

        if action == "cancel":
            self.clear(context)
            await query.edit_message_text("❌ Opération annulée.")
            return True

        if action == "confirm":
            data = dict(session.data)
            self.clear(context)
            await definition.on_confirm(update, context, data)
            return True

        if action == "prev":
            if session.step_index <= 0:
                await query.answer("Vous êtes déjà à la première étape.", show_alert=True)
                return True
            session.step_index -= 1
            session.editing = None
            self._save(context, session)
            await self._render_step(update, context, definition, session)
            return True

        if action == "next":
            step = definition.steps[session.step_index]
            if step.required and session.data.get(step.key) in (None, ""):
                await query.answer("Cette étape doit être renseignée.", show_alert=True)
                return True
            session.editing = None
            session.step_index += 1
            self._save(context, session)
            if session.step_index >= len(definition.steps):
                await self._render_summary(update, context, definition, session)
            else:
                await self._render_step(update, context, definition, session)
            return True

        if action == "edit" and len(parts) == 3 and definition.allow_edit:
            key = parts[2]
            index = next(
                (i for i, step in enumerate(definition.steps) if step.key == key),
                None,
            )
            if index is None:
                await query.edit_message_text("❌ Champ inconnu.")
                return True
            session.step_index = index
            session.editing = key
            self._save(context, session)
            await self._render_step(update, context, definition, session)
            return True

        if action == "choose" and len(parts) == 4:
            key, value = parts[2], parts[3]
            index = next(
                (i for i, step in enumerate(definition.steps) if step.key == key),
                None,
            )
            if index is None:
                await query.edit_message_text("❌ Choix inconnu.")
                return True

            session.data[key] = value
            if session.editing == key:
                session.editing = None
                self._save(context, session)
                await self._render_summary(update, context, definition, session)
                return True

            if session.step_index == index:
                session.step_index += 1
                self._save(context, session)
                if session.step_index >= len(definition.steps):
                    await self._render_summary(update, context, definition, session)
                else:
                    await self._render_step(update, context, definition, session)
            else:
                self._save(context, session)
                await self._render_summary(update, context, definition, session)
            return True

        await query.edit_message_text("❌ Action Wizard inconnue.")
        return True

    def _navigation_keyboard(self, session: WizardSession):
        buttons = []
        if session.step_index > 0:
            buttons.append(InlineKeyboardButton("⬅️ Précédent", callback_data=f"{self.CALLBACK_PREFIX}prev"))
        if session.step_index < len(self.definitions[session.name].steps) - 1:
            buttons.append(InlineKeyboardButton("➡️ Suivant", callback_data=f"{self.CALLBACK_PREFIX}next"))
        if not buttons:
            return None
        return InlineKeyboardMarkup([buttons])

    async def _render_step(self, update, context, definition, session):
        step = definition.steps[session.step_index]
        prefix = f"🧭 {definition.title}\n\n" if definition.title else ""
        text = prefix + step.prompt
        keyboard = step.keyboard(session.data) if step.keyboard else None
        nav = self._navigation_keyboard(session)
        if nav:
            nav_rows = [list(row) for row in (keyboard.inline_keyboard if keyboard else [])]
            nav_rows.extend(nav.inline_keyboard)
            keyboard = InlineKeyboardMarkup(nav_rows)
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text, reply_markup=keyboard, parse_mode="HTML"
            )
        else:
            await update.effective_message.reply_text(
                text, reply_markup=keyboard, parse_mode="HTML"
            )

    async def _render_summary(self, update, context, definition, session):
        buttons = []
        if definition.allow_edit:
            labels = {
                "lastname": "Nom",
                "firstname": "Prénom",
                "sex": "Sexe",
                "morphy": "Nature de l’adhérent",
                "phone": "Téléphone",
                "email": "Email",
                "address": "Adresse",
                "town": "Ville",
                "type_id": "Type d’adhérent",
                "date_adhesion": "Date d’adhésion",
            }
            for step in definition.steps:
                label = labels.get(step.key, step.key.replace("_", " ").capitalize())
                buttons.append([
                    InlineKeyboardButton(
                        f"✏️ {label}",
                        callback_data=f"{self.CALLBACK_PREFIX}edit:{step.key}",
                    )
                ])

        buttons.append([
            InlineKeyboardButton("✅ VALIDER", callback_data=f"{self.CALLBACK_PREFIX}confirm"),
            InlineKeyboardButton("❌ ANNULER", callback_data=f"{self.CALLBACK_PREFIX}cancel"),
        ])

        markup = InlineKeyboardMarkup(buttons)
        text = definition.summary(session.data)

        if update.callback_query:
            await update.callback_query.edit_message_text(
                text, reply_markup=markup, parse_mode="HTML"
            )
        else:
            await update.effective_message.reply_text(
                text, reply_markup=markup, parse_mode="HTML"
            )


def choice_keyboard(key: str, choices: list[tuple[str, str]]) -> KeyboardFactory:
    """Create an inline keyboard for short callback-safe values."""
    def factory(_data):
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(label, callback_data=f"wiz:choose:{key}:{value}")
            ]
            for label, value in choices
        ])

    return factory
