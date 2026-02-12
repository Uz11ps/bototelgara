from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, User
from aiogram.fsm.context import FSMContext

from services.content import content_manager
from bot.keyboards.main_menu import (
    build_pre_arrival_menu,
    build_in_house_menu,
    build_segment_reply_keyboard,
    build_reply_menu_from_key 
)

router = Router()

def get_menu_key_and_callback(label: str) -> tuple[str, str] | None:
    """Find menu key and callback_data for a given label."""
    menus_to_search = {
        "pre_arrival_menu": "pre_arrival_menu",
        "in_house_menu": "in_house_menu",
        "room_service.branches": "room_service_menu",
        # "breakfast.entry_menu": "breakfast_menu" 
    }
    
    for menu_config_key, menu_logic_key in menus_to_search.items():
        try:
            menu = content_manager.get_menu(menu_config_key)
            for item in menu:
                if item.get("label") == label:
                    return menu_config_key, item.get("callback_data")
        except (KeyError, ValueError):
            continue
            
    return None

@router.message(F.text)
async def handle_menu_text(message: Message, state: FSMContext):
    """Generic handler for menu text buttons."""
    text = message.text
    
    # Check for "Back"
    if text == "↩️ Назад":
        # Determine where to go back to based on state?
        # Or just show the main segment choice
        from bot.handlers.start import cmd_start
        # Reset to start
        await cmd_start(message, state)
        return

    # Check mapping
    result = get_menu_key_and_callback(text)
    if not result:
        return
        
    menu_key, callback_data = result
    
    # Execute Logic based on callback_data prefix
    # Pre-Arrival Logic
    if callback_data.startswith("pre_"):
        # Import logic (avoid circular imports inside function)
        from bot.handlers.pre_arrival import handle_pre_arrival_menu
        from bot.states import FlowState

        # Set the expected state!
        await state.set_state(FlowState.pre_arrival_menu)
        
        # Mocking
        mock_callback = CallbackQuery(
            id="mock",
            from_user=message.from_user,
            chat_instance="mock",
            message=message,
            data=callback_data
        )
        # We need to monkeypatch 'answer' to avoid error
        async def mock_answer(*args, **kwargs): pass
        mock_callback.answer = mock_answer
        
        # Call handler
        await handle_pre_arrival_menu(mock_callback, state)
        pass

    # In-House Logic
    elif callback_data.startswith("in_"):
        from bot.handlers.in_house import handle_in_house_menu
        from bot.states import FlowState
        
        # Set the expected state!
        await state.set_state(FlowState.in_house_menu)

        mock_callback = CallbackQuery(
            id="mock",
            from_user=message.from_user,
            chat_instance="mock",
            message=message,
            data=callback_data
        )
        async def mock_answer(*args, **kwargs): pass
        mock_callback.answer = mock_answer
        
        # Special case: room service adds a Reply Keyboard?
        if callback_data == "in_room_service":
             # We want to show room service options as Reply Buttons too?
             # For now, let's keep it simple. The user asked for "what is on the screen" (the level 1 submenus)
             pass

        await handle_in_house_menu(mock_callback, state)

    # Room Service Logic
    elif callback_data.startswith("rs_"):
         # Implement if needed
         pass
         
    return
