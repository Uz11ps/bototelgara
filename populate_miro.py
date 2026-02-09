"""
Populate Miro board with a comprehensive GORA Hotel Bot project schema (in Russian).
"""
import requests
import json
import time

TOKEN = "eyJtaXJvLm9yaWdpbiI6ImV1MDEifQ_qL03hAj8ycXK41y3q3EeFz_hM1o"
BOARD_ID = "uXjVGGNIgGQ="
BASE_URL = f"https://api.miro.com/v2/boards/{BOARD_ID}"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# --- Colors ---
CLR_ROOT = "#1a1a2e"
CLR_SUBSYSTEM = "#16213e"
CLR_BOT = "#0f3460"
CLR_HANDLER_GUEST = "#533483"
CLR_HANDLER_ADMIN = "#e94560"
CLR_SERVICE = "#0a6847"
CLR_DB = "#c84b31"
CLR_MODEL = "#d35400"
CLR_CONFIG = "#2c3e50"
CLR_CONTENT = "#8e44ad"
CLR_EXTERNAL = "#2980b9"
CLR_FRONTEND = "#27ae60"
CLR_MINIAPP = "#f39c12"
CLR_MIDDLEWARE = "#7f8c8d"

# Softer palette for readability
CLR_ROOT = "#1B2A4A"
CLR_SUBSYSTEM_BOT = "#2E86AB"
CLR_SUBSYSTEM_API = "#A23B72"
CLR_SUBSYSTEM_ADMIN_UI = "#F18F01"
CLR_SUBSYSTEM_MINIAPP = "#C73E1D"
CLR_SUBSYSTEM_SHELTER = "#3B1F2B"
CLR_SUBSYSTEM_DB = "#44803F"

CLR_HANDLER = "#E8D5B7"
CLR_SERVICE_BG = "#B8E0D2"
CLR_MODEL_BG = "#D6EADF"
CLR_CONFIG_BG = "#EAC4D5"
CLR_INFRA = "#95B8D1"


def clear_board():
    """Remove all existing items from the board."""
    print("Clearing existing board items...")
    for item_type in ["shapes", "connectors", "sticky_notes", "text", "frames"]:
        url = f"{BASE_URL}/items?type={item_type}&limit=50"
        try:
            resp = requests.get(url, headers=HEADERS)
            if resp.status_code == 200:
                items = resp.json().get("data", [])
                for item in items:
                    del_url = f"https://api.miro.com/v2/boards/{BOARD_ID}/items/{item['id']}"
                    requests.delete(del_url, headers=HEADERS)
                    time.sleep(0.15)
                if items:
                    print(f"  Deleted {len(items)} {item_type}")
        except Exception as e:
            print(f"  Error clearing {item_type}: {e}")
    # Also try generic items endpoint
    try:
        resp = requests.get(f"{BASE_URL}/items?limit=50", headers=HEADERS)
        if resp.status_code == 200:
            items = resp.json().get("data", [])
            for item in items:
                del_url = f"https://api.miro.com/v2/boards/{BOARD_ID}/items/{item['id']}"
                requests.delete(del_url, headers=HEADERS)
                time.sleep(0.15)
            if items:
                print(f"  Deleted {len(items)} remaining items")
    except Exception:
        pass
    time.sleep(1)
    print("Board cleared.")


def create_shape(content, x, y, width=200, height=100, color="#ffffff", text_color="#1a1a2e", font_size="14", border_color=None, shape="round_rectangle"):
    url = f"{BASE_URL}/shapes"
    style = {
        "fillColor": color,
        "textAlign": "center",
        "textAlignVertical": "middle",
        "fontFamily": "open_sans",
        "fontSize": font_size,
        "color": text_color,
        "borderWidth": "2",
        "borderColor": border_color or color,
        "borderOpacity": "1.0",
    }
    payload = {
        "data": {"content": content, "shape": shape},
        "style": style,
        "position": {"x": x, "y": y, "origin": "center"},
        "geometry": {"width": width, "height": height}
    }
    resp = requests.post(url, headers=HEADERS, json=payload)
    time.sleep(0.2)
    if resp.status_code == 201:
        sid = resp.json()["id"]
        print(f"  + Shape: {content[:40]}... -> {sid}")
        return sid
    else:
        print(f"  ! Error ({resp.status_code}): {resp.text[:120]}")
        return None


def create_connector(start_id, end_id, color="#333333", width="2", style_type="straight"):
    if not start_id or not end_id:
        return
    url = f"{BASE_URL}/connectors"
    payload = {
        "startItem": {"id": str(start_id)},
        "endItem": {"id": str(end_id)},
        "style": {
            "strokeColor": color,
            "strokeWidth": width,
        },
        "shape": style_type
    }
    resp = requests.post(url, headers=HEADERS, json=payload)
    time.sleep(0.15)
    if resp.status_code != 201:
        print(f"  ! Connector error ({resp.status_code}): {resp.text[:80]}")


def create_text(content, x, y, font_size="18", color="#1a1a2e", width=400):
    url = f"{BASE_URL}/text"
    payload = {
        "data": {"content": content},
        "style": {
            "fontSize": font_size,
            "color": color,
            "textAlign": "center"
        },
        "position": {"x": x, "y": y, "origin": "center"},
        "geometry": {"width": width}
    }
    resp = requests.post(url, headers=HEADERS, json=payload)
    time.sleep(0.15)
    if resp.status_code == 201:
        return resp.json()["id"]
    return None


def main():
    clear_board()
    print("\n=== Создание схемы проекта GORA Bot ===\n")

    # ═══════════════════════════════════════════
    # LEVEL 0: ROOT
    # ═══════════════════════════════════════════
    root = create_shape(
        "<b>GORA Hotel Bot</b><br>Телеграм-бот отеля «ГОРА»<br>Сортавала, Карелия",
        0, 0, 420, 120, "#1B2A4A", "#ffffff", "24"
    )

    # Description under root
    create_text(
        "<b>Полная архитектура проекта</b><br>"
        "Python • aiogram 3 • FastAPI • SQLAlchemy • SQLite • Shelter Cloud PMS",
        0, 100, "12", "#555555", 500
    )

    # ═══════════════════════════════════════════
    # LEVEL 1: MAIN SUBSYSTEMS
    # ═══════════════════════════════════════════
    y1 = 300
    subsystems = {}

    subsystems["bot"] = create_shape(
        "<b>🤖 Telegram Bot</b><br>(aiogram 3, FSM)<br>bot/main.py",
        -600, y1, 280, 100, "#2E86AB", "#ffffff", "16"
    )
    subsystems["api"] = create_shape(
        "<b>🌐 FastAPI Admin API</b><br>(REST, web_admin/)<br>Порт 8000",
        -200, y1, 280, 100, "#A23B72", "#ffffff", "16"
    )
    subsystems["admin_ui"] = create_shape(
        "<b>🖥 Админ-панель UI</b><br>(HTML/JS, admin_panel/)<br>Фронтенд",
        200, y1, 280, 100, "#F18F01", "#ffffff", "16"
    )
    subsystems["miniapp"] = create_shape(
        "<b>📱 Mini App</b><br>(Telegram WebApp)<br>Меню ресторана",
        600, y1, 280, 100, "#C73E1D", "#ffffff", "16"
    )
    subsystems["shelter"] = create_shape(
        "<b>🏨 Shelter Cloud PMS</b><br>(Внешний API)<br>pms.frontdesk24.ru",
        1000, y1, 280, 100, "#3B1F2B", "#ffffff", "16"
    )
    subsystems["database"] = create_shape(
        "<b>🗄 База данных</b><br>(SQLAlchemy + SQLite)<br>gora_bot.db",
        -1000, y1, 280, 100, "#44803F", "#ffffff", "16"
    )

    # Connect root to subsystems
    for key in subsystems:
        create_connector(root, subsystems[key], "#666666", "3", "curved")

    # ═══════════════════════════════════════════
    # LEVEL 2: BOT HANDLERS — Guest Features
    # ═══════════════════════════════════════════
    create_text("<b>Обработчики бота — Гостевые функции</b>", -600, 480, "14", "#2E86AB", 400)

    y2 = 580
    guest_handlers = [
        ("start.py", "Главное меню\n/start, /help"),
        ("check_in.py", "Заселение\nрегистрация, бронь дат"),
        ("booking.py", "Бронирование\n(Shelter API)"),
        ("menu_order.py", "Заказ из меню\nкорзина, оформление"),
        ("room_service.py", "Рум-сервис\nтех.проблемы, уборка"),
        ("cleaning_schedule.py", "Расписание уборок\nавтоматич. в 11:00"),
        ("pre_arrival.py", "До заезда\nинфо об отеле, FAQ"),
        ("in_house.py", "Проживание\nосновное меню гостя"),
        ("feedback.py", "Обратная связь\nопрос, оценка 1-5"),
        ("sos.py", "SOS\nэкстренная помощь"),
        ("guide.py", "Гид по Карелии\nприрода, кафе"),
        ("weather.py", "Погода\nСортавала, камеры"),
        ("loyalty.py", "Лояльность\nбаллы, личный кабинет"),
        ("additional_services.py", "Доп. услуги\nсап, лодки, баня"),
    ]

    handler_ids = []
    cols = 5
    x_start = -1100
    x_gap = 260
    y_gap = 140

    for idx, (name, desc) in enumerate(guest_handlers):
        col = idx % cols
        row = idx // cols
        x = x_start + col * x_gap
        y = y2 + row * y_gap
        hid = create_shape(
            f"<b>{name}</b><br>{desc}",
            x, y, 230, 110, "#E8D5B7", "#1a1a2e", "11"
        )
        handler_ids.append(hid)
        create_connector(subsystems["bot"], hid, "#2E86AB", "1", "curved")

    # ═══════════════════════════════════════════
    # LEVEL 2: BOT HANDLERS — Admin & Infra
    # ═══════════════════════════════════════════
    create_text("<b>Обработчики бота — Админ и инфраструктура</b>", 450, 480, "14", "#e94560", 400)

    admin_handlers = [
        ("admin.py", "Статус отеля\n/status, /rooms"),
        ("admin_panel.py", "Админ-панель в боте\nзаявки, ответы"),
        ("staff.py", "Панель персонала\nзадачи горничных"),
        ("webapp.py", "WebApp handler\nданные из Mini App"),
    ]

    y_admin = 580
    for idx, (name, desc) in enumerate(admin_handlers):
        x = 250 + idx * 260
        hid = create_shape(
            f"<b>{name}</b><br>{desc}",
            x, y_admin, 230, 110, "#FADBD8", "#1a1a2e", "11"
        )
        create_connector(subsystems["bot"], hid, "#e94560", "1", "curved")

    # ═══════════════════════════════════════════
    # LEVEL 2: BOT MIDDLEWARE & STATES
    # ═══════════════════════════════════════════
    mw = create_shape(
        "<b>middleware.py</b><br>ThrottlingMiddleware (0.25с)<br>CallbackAnswerMiddleware",
        -600, 950, 280, 90, "#D5D8DC", "#1a1a2e", "11"
    )
    states = create_shape(
        "<b>states.py (FSM)</b><br>FlowState: 30+ состояний<br>бронирование, меню, уборка...",
        -300, 950, 280, 90, "#D5D8DC", "#1a1a2e", "11"
    )
    keyboards = create_shape(
        "<b>keyboards/main_menu.py</b><br>Inline + Reply клавиатуры<br>для всех экранов",
        0, 950, 280, 90, "#D5D8DC", "#1a1a2e", "11"
    )
    create_connector(subsystems["bot"], mw, "#7f8c8d", "1")
    create_connector(subsystems["bot"], states, "#7f8c8d", "1")
    create_connector(subsystems["bot"], keyboards, "#7f8c8d", "1")

    # ═══════════════════════════════════════════
    # LEVEL 2: SERVICES
    # ═══════════════════════════════════════════
    create_text("<b>Сервисный слой (services/)</b>", -600, 1080, "14", "#0a6847", 300)

    y_svc = 1170
    svc_tickets = create_shape(
        "<b>tickets.py</b><br>Создание заявок<br>Rate-limit (3/мин)<br>CRUD операции",
        -900, y_svc, 250, 110, "#B8E0D2", "#1a1a2e", "12"
    )
    svc_admins = create_shape(
        "<b>admins.py</b><br>Уведомление админов<br>о новых заявках",
        -620, y_svc, 250, 110, "#B8E0D2", "#1a1a2e", "12"
    )
    svc_content = create_shape(
        "<b>content.py</b><br>ContentManager<br>Загрузка YAML текстов<br>Hot reload",
        -340, y_svc, 250, 110, "#B8E0D2", "#1a1a2e", "12"
    )
    svc_shelter = create_shape(
        "<b>shelter.py</b><br>ShelterClient API<br>getVariants, putOrder<br>Статистика отеля",
        -60, y_svc, 250, 110, "#B8E0D2", "#1a1a2e", "12"
    )
    svc_bridge = create_shape(
        "<b>bot_api_bridge.py</b><br>Мост бот ↔ API<br>Доставка сообщений<br>Poll каждые 5сек",
        220, y_svc, 250, 110, "#B8E0D2", "#1a1a2e", "12"
    )

    # Connect services to bot
    create_connector(subsystems["bot"], svc_tickets, "#0a6847", "1")
    create_connector(subsystems["bot"], svc_admins, "#0a6847", "1")
    create_connector(subsystems["bot"], svc_content, "#0a6847", "1")
    create_connector(subsystems["bot"], svc_shelter, "#0a6847", "1")
    create_connector(svc_bridge, subsystems["bot"], "#0a6847", "2", "curved")
    create_connector(svc_bridge, subsystems["api"], "#A23B72", "2", "curved")
    create_connector(svc_shelter, subsystems["shelter"], "#3B1F2B", "2", "curved")

    # ═══════════════════════════════════════════
    # LEVEL 2: FASTAPI ENDPOINTS
    # ═══════════════════════════════════════════
    create_text("<b>FastAPI эндпоинты (web_admin/main.py)</b>", 600, 480, "14", "#A23B72", 400)

    api_endpoints = [
        ("Заявки (Tickets)", "/api/tickets\nCRUD, статусы,\nсообщения"),
        ("Статистика", "/api/statistics\nза сегодня"),
        ("Меню", "/api/menu\nCRUD блюд,\nтоггл доступности"),
        ("Гид", "/api/guide\nCRUD мест\nи категорий"),
        ("Персонал", "/api/staff\nсотрудники, роли,\nправа доступа"),
        ("Камеры", "/api/camera\nRTSP → MJPEG\nffmpeg стрим"),
        ("Заказы", "/api/orders\nиз Mini App\nуведомления"),
        ("Shelter proxy", "/api/shelter/*\nдоступность,\nбронирования"),
    ]

    y_api = 580
    for idx, (name, desc) in enumerate(api_endpoints):
        col = idx % 4
        row = idx // 4
        x = 500 + col * 240
        y = y_api + row * 140
        eid = create_shape(
            f"<b>{name}</b><br>{desc}",
            x, y, 210, 110, "#F5B7B1", "#1a1a2e", "10"
        )
        create_connector(subsystems["api"], eid, "#A23B72", "1", "curved")

    # ═══════════════════════════════════════════
    # LEVEL 2: DATABASE MODELS
    # ═══════════════════════════════════════════
    create_text("<b>Модели базы данных (db/models.py)</b>", -600, 1340, "14", "#44803F", 400)

    y_db = 1440
    models = [
        ("Ticket", "Заявки гостей\nid, type, status,\nguest_chat_id, payload"),
        ("TicketMessage", "Сообщения в заявке\nsender: GUEST/ADMIN\ncontent, admin_name"),
        ("User", "Пользователи\ntelegram_id, phone\nloyalty_points"),
        ("AdminUser", "Администраторы\ntelegram_id\nis_active"),
        ("Staff", "Персонал\nроль: горничная,\nтехник, админ"),
        ("MenuItem", "Блюда меню\nкатегория, цена,\nсостав, доступность"),
        ("GuideItem", "Гид по местам\nприрода, кафе\nкарта, фото"),
        ("GuestBooking", "Бронирования гостей\nкомната, даты\nдля расписания уборок"),
        ("CleaningRequest", "Запросы на уборку\nдата, временной слот\nстатус"),
        ("StaffTask", "Задачи персонала\nкомната, тип,\nстатус, исполнитель"),
    ]

    for idx, (name, desc) in enumerate(models):
        col = idx % 5
        row = idx // 5
        x = -1100 + col * 280
        y = y_db + row * 140
        mid = create_shape(
            f"<b>{name}</b><br>{desc}",
            x, y, 250, 110, "#D6EADF", "#1a1a2e", "10"
        )
        create_connector(subsystems["database"], mid, "#44803F", "1", "curved")

    # ═══════════════════════════════════════════
    # ENUMS
    # ═══════════════════════════════════════════
    enums = create_shape(
        "<b>Перечисления (Enums)</b><br>"
        "TicketStatus: NEW, PENDING, COMPLETED, DECLINED<br>"
        "TicketType: ROOM_SERVICE, BREAKFAST, SOS, MENU_ORDER...<br>"
        "StaffRole: MAID, TECHNICIAN, ADMINISTRATOR<br>"
        "MenuCategory: breakfast, lunch, dinner",
        -600, 1730, 600, 110, "#EAC4D5", "#1a1a2e", "10"
    )
    create_connector(subsystems["database"], enums, "#44803F", "1")

    # ═══════════════════════════════════════════
    # CONTENT FILES
    # ═══════════════════════════════════════════
    create_text("<b>Контент и конфигурация</b>", 500, 1080, "14", "#8e44ad", 300)

    y_cfg = 1170
    cfg_config = create_shape(
        "<b>config.py</b><br>Settings dataclass<br>BOT_TOKEN, DB_URL<br>ADMIN_TOKEN, LOG_LEVEL",
        500, y_cfg, 240, 100, "#EAC4D5", "#1a1a2e", "11"
    )
    cfg_texts = create_shape(
        "<b>texts.ru.yml</b><br>Все текстовые сообщения<br>greeting, room_service,<br>breakfast, tickets...",
        760, y_cfg, 240, 100, "#EAC4D5", "#1a1a2e", "11"
    )
    cfg_menus = create_shape(
        "<b>menus.ru.yml</b><br>Структура меню<br>кнопки, навигация",
        1020, y_cfg, 240, 100, "#EAC4D5", "#1a1a2e", "11"
    )

    # ═══════════════════════════════════════════
    # ADMIN UI DETAILS
    # ═══════════════════════════════════════════
    admin_html = create_shape(
        "<b>admin_panel/index.html</b><br>SPA админ-панель<br>управление заявками, меню,<br>гидом, персоналом",
        200, 480, 260, 90, "#FAD7A0", "#1a1a2e", "10"
    )
    create_connector(subsystems["admin_ui"], admin_html, "#F18F01", "1")
    create_connector(admin_html, subsystems["api"], "#A23B72", "1", "curved")

    # ═══════════════════════════════════════════
    # MINI APP DETAILS
    # ═══════════════════════════════════════════
    mini_html = create_shape(
        "<b>mini_app/index.html</b><br>Telegram WebApp<br>визуальное меню ресторана<br>корзина → /api/orders",
        600, 420, 260, 90, "#F5CBA7", "#1a1a2e", "10"
    )
    create_connector(subsystems["miniapp"], mini_html, "#C73E1D", "1")

    # ═══════════════════════════════════════════
    # FLOW ARROWS (Key Data Flows)
    # ═══════════════════════════════════════════
    create_text(
        "<b>Ключевые потоки данных:</b><br>"
        "1. Гость → Бот → Заявка → БД → Уведомление админам<br>"
        "2. Админ (панель/бот) → Ответ → BotAPIBridge → Telegram гостю<br>"
        "3. Mini App → /api/orders → Заявка → Уведомление<br>"
        "4. Бот → Shelter API → Бронирование номера<br>"
        "5. Планировщик (11:00) → Промпт уборки → Гостям",
        0, 1900, 700, "12", "#333333"
    )

    # ═══════════════════════════════════════════
    # DEPLOYMENT INFO
    # ═══════════════════════════════════════════
    deploy = create_shape(
        "<b>🚀 Деплой и инфраструктура</b><br>"
        "Сервер: 89.104.66.21<br>"
        "Домен: gora.ru.net (HTTPS)<br>"
        "deploy.py / deploy.ps1<br>"
        "uvicorn (порт 8000) + aiogram polling",
        1000, 1170, 280, 130, "#95B8D1", "#1a1a2e", "11"
    )

    print("\n=== Схема проекта GORA Bot создана на Miro! ===")
    print(f"Ссылка: https://miro.com/app/board/{BOARD_ID}/")


if __name__ == "__main__":
    main()
