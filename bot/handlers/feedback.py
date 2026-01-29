from __future__ import annotations

import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.states import FlowState
from services.tickets import create_ticket, TicketRateLimitExceededError
from db.models import TicketType
from services.admins import notify_admins_about_ticket
from aiogram import Bot

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text == "/feedback")
async def start_feedback_manual(message: Message, state: FSMContext) -> None:
    await state.set_state(FlowState.feedback_rating)
    welcome_text = (
        "🌟 <b>Обратная связь</b>\n\n"
        "Нам очень важно ваше мнение! Пожалуйста, уделите минуту и ответьте на несколько вопросов.\n\n"
        "<b>Как вы оцениваете ваш отдых в отеле «ГОРА»?</b> (от 1 до 5)"
    )
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        builder.button(text=str(i), callback_data=f"rating_{i}")
    builder.adjust(5)
    
    await message.answer(welcome_text, reply_markup=builder.as_markup())

@router.callback_query(FlowState.feedback_rating, F.data.startswith("rating_"))
async def handle_feedback_rating(callback: CallbackQuery, state: FSMContext) -> None:
    rating = callback.data.split("_")[1]
    await state.update_data(feedback_rating=rating)
    await state.set_state(FlowState.feedback_liked)
    await callback.message.edit_text("<b>Что вам особенно понравилось во время пребывания?</b>")
    await callback.answer()

@router.message(FlowState.feedback_liked)
async def handle_feedback_liked(message: Message, state: FSMContext) -> None:
    await state.update_data(feedback_liked=message.text)
    await state.set_state(FlowState.feedback_improvements)
    await message.answer("<b>Есть ли что-то, что мы могли бы улучшить?</b>")

@router.message(FlowState.feedback_improvements)
async def handle_feedback_improvements(message: Message, state: FSMContext) -> None:
    await state.update_data(feedback_improvements=message.text)
    await state.set_state(FlowState.feedback_recommend)
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="Да", callback_data="recommend_yes")
    builder.button(text="Нет", callback_data="recommend_no")
    builder.adjust(2)
    
    await message.answer("<b>Хотели бы вы порекомендовать наш отель друзьям?</b>", reply_markup=builder.as_markup())

@router.callback_query(FlowState.feedback_recommend)
async def handle_feedback_recommend(callback: CallbackQuery, state: FSMContext) -> None:
    recommend = "Да" if callback.data == "recommend_yes" else "Нет"
    await state.update_data(feedback_recommend=recommend)
    await state.set_state(FlowState.feedback_comments)
    await callback.message.edit_text("<b>Есть ли дополнительные комментарии или пожелания?</b>")
    await callback.answer()

@router.message(FlowState.feedback_comments)
async def handle_feedback_finalize(message: Message, state: FSMContext) -> None:
    await state.update_data(feedback_comments=message.text)
    data = await state.get_data()
    
    summary = (
        f"📝 Новый отзыв от гостя:\n\n"
        f"Оценка: {data.get('feedback_rating')}/5\n"
        f"Понравилось: {data.get('feedback_liked')}\n"
        f"Улучшения: {data.get('feedback_improvements')}\n"
        f"Рекомендует: {data.get('feedback_recommend')}\n"
        f"Комментарий: {data.get('feedback_comments')}"
    )
    
    try:
        ticket = create_ticket(
            type_=TicketType.FEEDBACK,
            guest_chat_id=str(message.from_user.id),
            guest_name=message.from_user.full_name,
            room_number=None,
            initial_message=summary,
        )
    except TicketRateLimitExceededError:
        pass # Ignore for feedback

    await message.answer(
        "✨ <b>Большое спасибо за ваш отзыв!</b>\n\n"
        "Ваше мнение помогает нам становиться лучше. Надеемся увидеть вас снова!"
    )
    
    # Send link to external review platforms if rating is high
    if int(data.get('feedback_rating', '0')) >= 4:
        await message.answer(
            "Будем очень признательны, если вы продублируете ваш отзыв на Яндекс Картах или Яндекс Путешествиях:\n"
            "https://yandex.ru/maps/org/gora/..."
        )
    
    bot: Bot = message.bot
    await notify_admins_about_ticket(bot, ticket, summary)
    
    await state.clear()
