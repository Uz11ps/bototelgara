from __future__ import annotations

from aiogram.fsm.context import FSMContext

NAV_STACK_KEY = "_nav_stack"

VIEW_SEGMENT = "segment"
VIEW_PRE_ARRIVAL = "pre_arrival"
VIEW_IN_HOUSE = "in_house"
VIEW_ROOM_SERVICE = "room_service"
VIEW_EVENTS = "events"
VIEW_MENU = "menu"


async def nav_reset(state: FSMContext, *views: str) -> None:
    stack = [v for v in views if v]
    await state.update_data(**{NAV_STACK_KEY: stack})


async def nav_push(state: FSMContext, view: str) -> None:
    data = await state.get_data()
    stack = list(data.get(NAV_STACK_KEY) or [])
    if not stack or stack[-1] != view:
        stack.append(view)
    await state.update_data(**{NAV_STACK_KEY: stack})


async def nav_back(state: FSMContext) -> str:
    data = await state.get_data()
    stack = list(data.get(NAV_STACK_KEY) or [])
    if len(stack) > 1:
        stack.pop()
    target = stack[-1] if stack else VIEW_SEGMENT
    await state.update_data(**{NAV_STACK_KEY: stack})
    return target
