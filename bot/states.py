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

    # Booking flow (Shelter API)
    booking_check_in = State()
    booking_check_out = State()
    booking_adults = State()
    booking_select_variant = State()
    booking_guest_name = State()
    booking_guest_phone = State()
    booking_guest_email = State()
    booking_confirm = State()

    admin_reply = State()

    # Menu ordering flow with cart
    menu_category_choice = State()
    menu_item_selection = State()
    menu_cart_review = State()
    menu_guest_name = State()  # Ask guest name
    menu_room_number = State()  # Ask room number
    menu_guest_comment = State()
    menu_confirm_order = State()

    # Guest booking capture for cleaning schedule
    guest_room_number = State()
    guest_check_in_date = State()
    guest_check_out_date = State()

    # Cleaning schedule selection
    cleaning_time_selection = State()
