from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse
import html

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import or_

from bot.navigation import VIEW_EVENTS, nav_push
from db.models import EventItem
from db.session import SessionLocal


router = Router()
PUBLIC_BASE_URL = "https://gora.ru.net"


def _get_active_events() -> list[EventItem]:
    now = datetime.utcnow()
    with SessionLocal() as db:
        items = db.query(EventItem).filter(
            EventItem.is_active == True,
            or_(EventItem.publish_from.is_(None), EventItem.publish_from <= now),
            or_(EventItem.publish_until.is_(None), EventItem.publish_until >= now),
        ).order_by(EventItem.starts_at.asc()).all()
        for item in items:
            db.expunge(item)
        return items


def _is_valid_url(url: str | None) -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _to_public_url(url: str | None) -> str | None:
    if not url:
        return None
    value = url.strip()
    if value.startswith("/"):
        return f"{PUBLIC_BASE_URL}{value}"
    return value


@router.callback_query(F.data == "pre_events_banquets")
async def show_events(callback: CallbackQuery, state: FSMContext | None = None) -> None:
    await callback.answer()
    if state is not None:
        await nav_push(state, VIEW_EVENTS)
    events = _get_active_events()
    if not events:
        await callback.message.answer("На данный момент нет никаких мероприятий.")
        return

    buttons = [[InlineKeyboardButton(text=item.name, callback_data=f"event_item:{item.id}")] for item in events]
    buttons.append([InlineKeyboardButton(text="↩️ Назад", callback_data="nav:back")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer("Выберите мероприятие:", reply_markup=kb)


@router.callback_query(F.data.startswith("event_item:"))
async def show_event_details(callback: CallbackQuery) -> None:
    await callback.answer()
    item_id = int((callback.data or "").split(":", 1)[1])
    with SessionLocal() as db:
        item = db.query(EventItem).filter(EventItem.id == item_id).first()
        if not item:
            await callback.message.answer("Мероприятие не найдено.")
            return
        db.expunge(item)

    starts = item.starts_at.strftime("%d.%m.%Y %H:%M")
    ends = item.ends_at.strftime("%d.%m.%Y %H:%M")

    text = (
        f"🎉 <b>{html.escape(item.name)}</b>\n\n"
        f"{html.escape(item.description)}\n\n"
        f"🗓 <b>Когда:</b> {starts} — {ends}\n"
    )
    if item.location_text:
        text += f"📍 <b>Где:</b> {html.escape(item.location_text)}\n"
    if _is_valid_url(item.map_url):
        text += f"🗺 <a href=\"{html.escape(item.map_url)}\">Открыть на карте</a>\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ К мероприятиям", callback_data="pre_events_banquets")]
    ])

    image_url = _to_public_url(item.image_url)
    if _is_valid_url(image_url):
        try:
            await callback.message.answer_photo(photo=image_url, caption=text, parse_mode="HTML", reply_markup=kb)
            return
        except Exception:
            text += f"\n🖼 Фото не удалось загрузить автоматически: {html.escape(str(image_url))}\n"
    elif item.image_url:
        text += f"\n🖼 Некорректная ссылка на фото: {html.escape(item.image_url)}\n"
    await callback.message.answer(text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)
