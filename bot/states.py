from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class FlowState(StatesGroup):
    choosing_segment = State()
    pre_arrival_menu = State()
    in_house_menu = State()

    room_service_choosing_branch = State()
    room_service_room_number = State()
    room_service_technical_category = State()
    room_service_technical_details = State()

    room_service_extra_item = State()
    room_service_extra_quantity = State()

    room_service_cleaning_time = State()
    room_service_cleaning_comments = State()

    room_service_pillow_choice = State()

    room_service_other_text = State()

    breakfast_entry = State()
    breakfast_persons = State()
    breakfast_confirm = State()
    breakfast_after_deadline_choice = State()
    
    additional_services_menu = State()
    additional_services_booking = State()
    
    feedback_rating = State()
    feedback_liked = State()
    feedback_improvements = State()
    feedback_recommend = State()
    feedback_comments = State()
    
    contact_admin_type = State()
    contact_admin_message = State()

    admin_reply = State()
