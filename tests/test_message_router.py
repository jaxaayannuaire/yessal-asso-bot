import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from modules.message_router import message_text_router


@pytest.mark.asyncio
async def test_routes_to_contact_filter_first():
    update, context = MagicMock(), MagicMock()
    with patch('modules.message_router.handle_contact_filter_input', new=AsyncMock(return_value=True)) as contact, \
         patch('modules.message_router.handle_member_filter_input', new=AsyncMock(return_value=False)) as member, \
         patch('modules.message_router.wizard_text_router', new=AsyncMock()) as wizard:
        await message_text_router(update, context)
    contact.assert_awaited_once_with(update, context)
    member.assert_not_awaited()
    wizard.assert_not_awaited()


@pytest.mark.asyncio
async def test_routes_to_member_filter_when_contact_inactive():
    update, context = MagicMock(), MagicMock()
    with patch('modules.message_router.handle_contact_filter_input', new=AsyncMock(return_value=False)), \
         patch('modules.message_router.handle_member_filter_input', new=AsyncMock(return_value=True)) as member, \
         patch('modules.message_router.wizard_text_router', new=AsyncMock()) as wizard:
        await message_text_router(update, context)
    member.assert_awaited_once_with(update, context)
    wizard.assert_not_awaited()


@pytest.mark.asyncio
async def test_routes_to_wizard_when_no_search_filter_active():
    update, context = MagicMock(), MagicMock()
    with patch('modules.message_router.handle_contact_filter_input', new=AsyncMock(return_value=False)), \
         patch('modules.message_router.handle_member_filter_input', new=AsyncMock(return_value=False)), \
         patch('modules.message_router.wizard_text_router', new=AsyncMock()) as wizard:
        await message_text_router(update, context)
    wizard.assert_awaited_once_with(update, context)
