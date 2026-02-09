# GORA Telegram bot (Milestone A)

### Overview

This repository contains the **Telegram-only MVP bot** for the premium hotel **GORA** (Сортавала, Карелия), implementing **Milestone A**:

- **Telegram bot skeleton** built with Python 3.12 and aiogram v3.
- **Ticketing system** (room-service requests → tickets + ticket messages in SQLite via SQLAlchemy).
- **File-based YAML content system** for all user-facing Russian texts and menus.
- Minimal **admin notification stub** that can notify configured admins about new tickets (no web panel yet).

---

### Tech stack

- **Python**: 3.12
- **Telegram bot**: aiogram v3
- **DB / ORM**: SQLite + SQLAlchemy 2.x
- **Content**: YAML files under `content/` loaded via `services.content.ContentManager`
- **Tests**: pytest (minimal unit tests)

---

### Project structure

- **bot/** – Telegram bot logic
  - `bot/main.py` – entrypoint to start the bot.
  - `bot/handlers/` – handlers for `/start`, pre-arrival menu, in-house menu, room service flows.
  - `bot/states.py` – FSM states for conversational flows.
  - `bot/keyboards/` – inline keyboards built from YAML menus.
- **db/** – database models and session
  - `db/base.py` – SQLAlchemy Base.
  - `db/models.py` – `Ticket`, `TicketMessage`, `AdminUser` models and enums.
  - `db/session.py` – engine + `SessionLocal` + `init_db()`.
- **services/** – shared services
  - `services/content.py` – YAML content loader (`texts.ru.yml`, `menus.ru.yml`).
  - `services/tickets.py` – ticket creation and helper queries.
  - `services/admins.py` – admin notification stub.
- **content/** – editable Russian content
  - `content/texts.ru.yml` – greetings, prompts, confirmations.
  - `content/menus.ru.yml` – segment / pre-arrival / in-house / room-service menus.
- **tests/** – minimal tests
  - `tests/test_ticket_creation.py` – verifies ticket + message persistence.
  - `tests/test_content_loading.py` – verifies YAML content loading.
- **config.py** – environment-driven settings wrapper.
- **requirements.txt** – Python dependencies.
- **.env.example** – sample env vars (no secrets).
- **.gitignore** – excludes `.env`, virtualenv, caches, DB file.

---

### Configuration & environment

> **Security note:** Never commit real secrets. Do not log secrets. Use environment variables only.
> The Telegram bot token used for this project **must be treated as a secret**. If it was ever exposed (e.g., in code or logs), rotate/regenerate it in BotFather and update your local `.env` file.

Create a local `.env` file (this file is ignored by Git) based on `.env.example`:

```env
TELEGRAM_BOT_TOKEN=__PUT_REAL_TOKEN_HERE__
DATABASE_URL="sqlite:///./gora_bot.db"
ADMIN_REGISTRATION_TOKEN="set-a-strong-admin-registration-token"
LOG_LEVEL="INFO"
```

- **TELEGRAM_BOT_TOKEN** – Telegram bot token from BotFather.
- **DATABASE_URL** – SQLAlchemy database URL. Default in code is `sqlite:///./gora_bot.db`.
- **ADMIN_REGISTRATION_TOKEN** – reserved for future protected admin registration (not yet used heavily in Milestone A).
- **LOG_LEVEL** – log level (e.g. `INFO`, `DEBUG`).

> The code never prints the values of these variables, only uses them internally.

---

### Installation

1. **Create & activate a virtual environment** (example for Windows PowerShell):

   ```powershell
   cd hotel_bot_try
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

2. **Install dependencies**:

   ```powershell
   pip install -r requirements.txt
   ```

3. **Create `.env`** from `.env.example` and fill in your real values (do not commit `.env`).

4. **Initialize the database** (happens automatically on first run via `init_db()` called from `bot/main.py`).

---

### Running the bot locally

1. Ensure your virtual environment is active and `.env` is configured with a valid `TELEGRAM_BOT_TOKEN`.

2. Start the bot:

   ```powershell
   python -m bot.main
   ```

3. In Telegram, send `/start` to your bot:
   - You will see a **premium Russian greeting** loaded from `content/texts.ru.yml`.
   - You will be asked to choose:
     - "Я планирую поездку" (pre-arrival)
     - "Я уже проживаю в отеле" (in-house)

4. Navigation:
   - **Pre-arrival menu** (all items and texts from YAML):
     - 🏨 Забронировать номер
     - 🛏 Номера и цены
     - 🌲 Об отеле
     - 🎉 Мероприятия и банкеты
     - 📍 Как добраться
     - ❓ Вопросы и ответы
     - 🍽 Ресторан
     - 📞 Связаться с администратором
   - **In-house menu**:
     - 🛎 Рум‑сервис
     - 🌲 Прогулки и отдых
     - 🍽 Ресторан
     - 🎒 Рекомендации
     - 📞 Администратор
     - Дополнительные услуги

5. **Room service module** (from in-house menu → "🛎 Рум‑сервис"):
   - Bot asks: "Что вам нужно?" and shows branches:
     - Техническая проблема
     - Дополнительно в номер
     - Уборка номера
     - Меню подушек
     - Другое
   - Each branch launches a short dialog and **creates a ticket**.

---

### Ticketing behavior (Milestone A)

- **Models** (in `db/models.py`):
  - `Ticket` – stores core ticket data: type (`ROOM_SERVICE` / etc.), status, guest chat id, name, payload JSON.
  - `TicketMessage` – stores textual representation of the request (per ticket), with sender (`GUEST`, `ADMIN`, `SYSTEM`).
- **Creation**:
  - Code path: handlers in `bot/handlers/room_service.py` → `services.tickets.create_ticket()`.
  - For each room-service branch, the bot builds a **summary string** based on YAML templates and persists:
    - A `Ticket` row.
    - A `TicketMessage` row (initial guest-side request summary).
- **Status**:
  - New tickets are created with status `PENDING_ADMIN` (state machine will be extended in later milestones).
- **Confirmation to guest**:
  - After ticket creation, user receives a **premium Russian confirmation** from `content/texts.ru.yml`:
    - `tickets.created_confirmation` with `{ticket_id}` placeholder.

---

### Admin notification stub (temporary)

There is **no web panel yet** in Milestone A. Instead, we provide a minimal stub:

- Model `AdminUser` (in `db/models.py`) holds potential admin Telegram IDs.
- `services.admins.notify_admins_about_ticket(bot, ticket, summary)`:
  - Looks up **active admins** from DB.
  - If none are found, it **silently does nothing** (bot still creates tickets successfully).
  - If admins exist, bot sends them a notification message using template `admin.new_ticket_notification` from `texts.ru.yml`.
- You can manually create rows in `admin_users` table (e.g., via a DB tool or future CLI) to enable notifications.

> There is no hardcoded `ADMIN_CHAT_ID`. All admin linking is DB-based.

---

### Content system

- All user-facing Russian strings and menu labels come from YAML under `content/`:
  - `content/texts.ru.yml` – greetings, prompts, confirmations, informational texts.
  - `content/menus.ru.yml` – segment / pre-arrival / in-house / room-service menus.
- The loader `services.content.ContentManager`:
  - Loads both YAML files on first use.
  - Provides:
    - `get_text(key: str) -> str` – e.g. `"greeting.start"`, `"tickets.created_confirmation"`.
    - `get_menu(key: str) -> list[dict]` – e.g. `"segment_menu"`, `"pre_arrival_menu"`, `"in_house_menu"`, `"room_service.branches"`.
  - Keys are **nested** using dot notation (e.g., `room_service.technical_problem.prompt_details`).

#### Reloading content at runtime

For Milestone A there is a simple command to reload content without restarting the process (for admins only):

- Telegram command: `/reload_content`
  - Handler: `bot/handlers/start.py`.
  - Only works for users whose Telegram ID is present as an active row in the `admin_users` table.
  - Calls `content_manager.reload()` and replies with `system.content_reloaded` text.
  - Other users receive a polite "not authorized" message from `system.not_authorized`.

In all cases you can **edit YAML and restart the bot** to pick up changes.

---

### Tests

Run tests with:

```powershell
pytest
```

Included tests:

- **`tests/test_ticket_creation.py`**
  - Uses an in-memory SQLite database.
  - Calls `create_ticket()` and verifies:
    - `Ticket` is persisted with type `ROOM_SERVICE` and status `PENDING_ADMIN`.
    - Exactly one `TicketMessage` is created with sender `GUEST` and correct content.

- **`tests/test_content_loading.py`**
  - Creates a temporary `content/` directory.
  - Writes simple `texts.ru.yml` and `menus.ru.yml` files.
  - Verifies that `ContentManager` loads them and returns expected values.

---

### Manual test checklist (Milestone A)

Use this checklist to validate Milestone A end-to-end:

- **Environment & startup**
  - [ ] `.env` created from `.env.example` with valid `TELEGRAM_BOT_TOKEN` and (optional) custom `DATABASE_URL`.
  - [ ] Bot starts successfully via `python -m bot.main` without logging secrets.
  - [ ] `gora_bot.db` (or chosen SQLite file) appears after first run.

- **/start and segment selection**
  - [ ] `/start` shows premium Russian greeting from YAML (no hardcoded text).
  - [ ] Bot asks to choose between "Я планирую поездку" and "Я уже проживаю в отеле".
  - [ ] Choosing each option opens the corresponding menu with correct labels from YAML.

- **Pre-arrival menu**
  - [ ] All 8 items are visible with emojis and labels matching the specification.
  - [ ] Tapping any item sends an informational message loaded from YAML.

- **In-house menu**
  - [ ] All items are visible and respond with informative text from YAML, except "🛎 Рум‑сервис", which starts the room-service flow.

- **Room-service flows (ticket creation)**
  - [ ] **Technical problem**:
    - [ ] Bot asks for problem type, then optional details.
    - [ ] After replying, a ticket is created and bot sends confirmation with ticket id.
  - [ ] **Extra to room**:
    - [ ] Bot asks what to bring, then quantity.
    - [ ] Ticket is created with correct summary, confirmation received.
  - [ ] **Cleaning**:
    - [ ] Bot asks for preferred time, then comments.
    - [ ] Ticket is created, confirmation received.
  - [ ] **Pillow menu**:
    - [ ] Bot asks for pillow preference; after answer, ticket is created.
  - [ ] **Other**:
    - [ ] Bot asks to describe request; after answer, ticket is created.
  - [ ] In all cases, tickets are stored in SQLite, each with one `TicketMessage` row.

- **Admin notification stub**
  - [ ] With no `admin_users` rows, new tickets are created without errors (no notification expected).
  - [ ] After manually adding an `admin_users` row with a valid Telegram id, new tickets trigger a notification message to that chat with a summary.

- **Content system**
  - [ ] Editing `content/texts.ru.yml` (e.g., greeting) and restarting bot updates texts in Telegram.
  - [ ] Running `/reload_content` after editing YAML updates texts without restart.

If all the above points pass, **Milestone A is implemented and working**. Later milestones will add the admin web panel, breakfast ordering, and extended ticket state machine.
