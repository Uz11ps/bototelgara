const API_BASE = '/api';

class AdminApp {
    constructor() {
        this.tickets = [];
        this.currentTicket = null;
        this.stats = null;
        this.hotelParams = null;
        this.availability = null;
        this.menu = [];
        this.menuCategorySettings = {};
        this.guide = [];
        this.events = [];
        this.staffTasks = [];
        this.users = [];
        this.staff = [];
        this.menusYamlContent = '';
        this.menusYamlStatus = '';
        this.menusJson = null;
        this.textsYamlContent = '';
        this.textsYamlStatus = '';
        this.textsJson = null;
        this.buttonLabels = [];
        this.buttonLabelsStatus = '';
        this.currentTab = 'tickets';
        this.ticketStatusFilter = null;
        this.isUserAdmin = false;
        this.editingMenuItem = null;
        this.editingGuideItem = null;
        this.editingEventItem = null;
        this.editingStaff = null;
        this.tempCompositionItems = [];
        this.messageDraft = '';
        this.ticketDetailScrollBottomGap = 0;
        this.init();
    }

    async init() {
        this.render();
        const isAdmin = await this.checkAdminStatus();
        this.isUserAdmin = isAdmin;

        if (isAdmin) {
            this.currentTab = 'tickets';
            await Promise.all([
                this.loadStatistics(),
                this.loadTickets(),
                this.loadHotelParams(),
                this.loadMenu(),
                this.loadMenuCategorySettings(),
                this.loadGuide(),
                this.loadEvents(),
                this.loadMenusYaml(),
                this.loadMenusJson(),
                this.loadTextsYaml(),
                this.loadTextsJson(),
                this.loadButtonLabels(),
                this.loadStaffTasks(),
                this.loadUsers(),
                this.loadStaff()
            ]);
        } else {
            this.currentTab = 'guest_home';
            await Promise.all([
                this.loadMenu(),
                this.loadGuide(),
                this.loadHotelParams()
            ]);
        }
        this.render();

        setInterval(() => {
            if (this.isUserAdmin) {
                if (this.currentTab === 'tickets') {
                    this.loadStatistics();
                    this.loadTickets();
                    // Не обновлять детали заявки, если пользователь печатает в поле ответа (иначе курсор сбрасывается)
                    const input = document.getElementById('messageInput');
                    const userIsTyping = input && document.activeElement === input;
                    if (this.currentTicket?.id && !userIsTyping) {
                        this.loadTicketDetail(this.currentTicket.id, { preserveUiState: true });
                    }
                }
                // Only refresh staff if not editing
                if (this.currentTab === 'staff_management' && !this.editingStaff) {
                    this.loadStaff();
                }
            }
        }, 10000);
    }

    async checkAdminStatus() {
        const urlParams = new URLSearchParams(window.location.search);
        if (window.location.pathname === '/admin' || urlParams.get('admin') === 'true') return true;
        if (window.Telegram?.WebApp?.initDataUnsafe?.user) {
            const user = window.Telegram.WebApp.initDataUnsafe.user;
            try {
                const response = await fetch(`${API_BASE}/check-admin?telegram_id=${user.id}`);
                const result = await response.json();
                return result.is_admin;
            } catch (e) { return false; }
        }
        return false;
    }

    async loadStatistics() {
        try {
            const response = await fetch(`${API_BASE}/statistics`);
            this.stats = await response.json();
            this.renderStatistics();
        } catch (e) { console.error(e); }
    }

    async loadTickets(status = this.ticketStatusFilter) {
        try {
            this.ticketStatusFilter = status ?? null;
            const url = this.ticketStatusFilter ? `${API_BASE}/tickets?status=${this.ticketStatusFilter}` : `${API_BASE}/tickets`;
            const response = await fetch(url);
            this.tickets = await response.json();
            this.renderTicketList();
        } catch (e) { console.error(e); }
    }

    async loadTicketDetail(id, { preserveUiState = false } = {}) {
        try {
            if (preserveUiState && this.currentTicket?.id === id) {
                this.captureTicketDetailUiState();
            } else {
                this.messageDraft = '';
                this.ticketDetailScrollBottomGap = 0;
            }
            const response = await fetch(`${API_BASE}/tickets/${id}`);
            this.currentTicket = await response.json();
            this.renderTicketDetail();
            this.restoreTicketDetailUiState();
        } catch (e) {
            console.error(e);
        }
    }

    captureTicketDetailUiState() {
        const input = document.getElementById('messageInput');
        if (input) {
            this.messageDraft = input.value;
        }
        const messagesBox = document.getElementById('ticketMessagesContainer');
        if (messagesBox) {
            this.ticketDetailScrollBottomGap = Math.max(
                messagesBox.scrollHeight - messagesBox.scrollTop - messagesBox.clientHeight,
                0
            );
        }
    }

    restoreTicketDetailUiState() {
        requestAnimationFrame(() => {
            const input = document.getElementById('messageInput');
            if (input) {
                input.value = this.messageDraft || '';
            }
            const messagesBox = document.getElementById('ticketMessagesContainer');
            if (messagesBox) {
                const targetScrollTop = messagesBox.scrollHeight - messagesBox.clientHeight - this.ticketDetailScrollBottomGap;
                messagesBox.scrollTop = Math.max(targetScrollTop, 0);
            }
        });
    }

    async loadHotelParams() {
        try {
            const response = await fetch(`${API_BASE}/shelter/hotel-params`);
            const result = await response.json();
            if (result && result.settings) {
                this.hotelParams = result;
            } else if (result && result.data) {
                const d = result.data;
                this.hotelParams = {
                    settings: d[0]?.[0] || {},
                    amenities: d[3] || [],
                    rates: d[4] || [],
                    categories: d[6] || [],
                    hotel_info: d[7]?.[0] || { hotelName: 'Отель Гора' }
                };
            }
            if (this.currentTab === 'shelter') this.render();
        } catch (e) { console.error(e); }
    }

    async loadMenu() {
        try {
            const r = await fetch(`${API_BASE}/menu`);
            this.menu = await r.json();
        } catch (e) { console.error(e); }
    }

    async loadMenuCategorySettings() {
        try {
            const r = await fetch(`${API_BASE}/menu/category-settings`);
            this.menuCategorySettings = await r.json();
        } catch (e) { console.error(e); }
    }

    async loadGuide() {
        try {
            const r = await fetch(`${API_BASE}/guide`);
            this.guide = await r.json();
        } catch (e) { console.error(e); }
    }

    async loadEvents() {
        try {
            const r = await fetch(`${API_BASE}/events`);
            this.events = await r.json();
        } catch (e) { console.error(e); }
    }

    async loadMenusJson() {
        try {
            const r = await fetch(`${API_BASE}/content/menus-ru/json`);
            this.menusJson = await r.json();
        } catch (e) {
            console.error(e);
        }
    }

    async loadTextsJson() {
        try {
            const r = await fetch(`${API_BASE}/content/texts-ru/json`);
            this.textsJson = await r.json();
        } catch (e) {
            console.error(e);
        }
    }

    async loadMenusYaml() {
        try {
            const r = await fetch(`${API_BASE}/content/menus-ru`);
            const data = await r.json();
            this.menusYamlContent = data.content || '';
        } catch (e) {
            console.error(e);
        }
    }

    async loadTextsYaml() {
        try {
            const r = await fetch(`${API_BASE}/content/texts-ru`);
            const data = await r.json();
            this.textsYamlContent = data.content || '';
        } catch (e) {
            console.error(e);
        }
    }

    async loadButtonLabels() {
        try {
            const r = await fetch(`${API_BASE}/content/button-labels`);
            const data = await r.json();
            this.buttonLabels = data.buttons || [];
        } catch (e) {
            console.error(e);
        }
    }

    async loadStaffTasks() {
        try {
            const r = await fetch(`${API_BASE}/staff/tasks`);
            this.staffTasks = await r.json();
            if (this.currentTab === 'staff') this.render();
        } catch (e) { console.error(e); }
    }

    async loadUsers() {
        try {
            const r = await fetch(`${API_BASE}/users`);
            this.users = await r.json();
        } catch (e) { console.error(e); }
    }

    async loadStaff() {
        try {
            const r = await fetch(`${API_BASE}/staff?t=${Date.now()}`);
            this.staff = await r.json();
            if (this.currentTab === 'staff_management' && !this.editingStaff) this.render();
        } catch (e) { console.error(e); }
    }

    async saveMenuItem(item) {
        const method = item.id ? 'PUT' : 'POST';
        const url = item.id ? `${API_BASE}/menu/${item.id}` : `${API_BASE}/menu`;
        await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(item)
        });
        this.editingMenuItem = null;
        await this.loadMenu();
        this.render();
    }

    async deleteMenuItem(id) {
        if (!confirm('Удалить это блюдо?')) return;
        await fetch(`${API_BASE}/menu/${id}`, { method: 'DELETE' });
        await this.loadMenu();
        this.render();
    }

    addCompositionItem() {
        const nameInput = document.getElementById('newIngredientName');
        const qtyInput = document.getElementById('newIngredientQty');
        const unitInput = document.getElementById('newIngredientUnit');

        const name = nameInput?.value.trim();
        const quantity = qtyInput?.value.trim();
        const unit = unitInput?.value.trim();

        if (!name) return alert('Укажите название ингредиента');

        this.tempCompositionItems = this.tempCompositionItems || [];
        this.tempCompositionItems.push({
            name: name,
            quantity: quantity ? parseInt(quantity) : null,
            unit: unit || null
        });

        nameInput.value = '';
        qtyInput.value = '';
        unitInput.value = '';

        this.updateCompositionListDisplay();
    }

    removeCompositionItem(idx) {
        this.tempCompositionItems.splice(idx, 1);
        this.updateCompositionListDisplay();
    }

    updateCompositionListDisplay() {
        const compositionListHTML = this.tempCompositionItems.map((item, idx) => {
            const qtyUnit = item.quantity && item.unit ? ` - ${item.quantity} ${item.unit}` : '';
            return `
                <div class="flex items-center gap-2 bg-white p-2 rounded border mb-1">
                    <span class="flex-1"><b>${item.name}</b>${qtyUnit}</span>
                    <button onclick="app.removeCompositionItem(${idx})" class="text-red-500 hover:bg-red-100 px-2 py-1 rounded">✕</button>
                </div>
            `;
        }).join('') || '<div class="text-gray-400 text-sm">Нет ингредиентов</div>';
        document.getElementById('compositionList').innerHTML = compositionListHTML;
    }

    async saveMenuItemWithComposition() {
        const m = this.editingMenuItem;
        const item = {
            id: m.id || null,
            name: document.getElementById('menuName').value,
            price: parseInt(document.getElementById('menuPrice').value),
            category: document.getElementById('menuCategory').value,
            category_type: document.getElementById('menuCategory').value,
            description: document.getElementById('menuDesc').value,
            composition: this.tempCompositionItems,
            admin_comment: document.getElementById('menuComment').value,
            is_available: true
        };
        await this.saveMenuItem(item);
        this.tempCompositionItems = [];
    }

    async toggleMenuItem(id) {
        await fetch(`${API_BASE}/menu/${id}/toggle`, { method: 'PATCH' });
        await this.loadMenu();
        this.render();
    }

    async toggleMenuCategory(category) {
        const current = !!this.menuCategorySettings?.[category];
        await fetch(`${API_BASE}/menu/category/${category}/enabled`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_enabled: !current })
        });
        await this.loadMenuCategorySettings();
        this.render();
    }

    async saveGuideItem(item) {
        const method = item.id ? 'PUT' : 'POST';
        const url = item.id ? `${API_BASE}/guide/${item.id}` : `${API_BASE}/guide`;
        await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(item)
        });
        this.editingGuideItem = null;
        await this.loadGuide();
        this.render();
    }

    async saveEventItem(item) {
        const method = item.id ? 'PUT' : 'POST';
        const url = item.id ? `${API_BASE}/events/${item.id}` : `${API_BASE}/events`;
        await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(item)
        });
        this.editingEventItem = null;
        await this.loadEvents();
        this.render();
    }

    async uploadEventImage() {
        const fileInput = document.getElementById('eventImageFile');
        const urlInput = document.getElementById('eventImageUrl');
        if (!fileInput || !urlInput || !fileInput.files || !fileInput.files.length) {
            alert('Выберите файл изображения');
            return;
        }
        const file = fileInput.files[0];
        const formData = new FormData();
        formData.append('file', file);
        const resp = await fetch(`${API_BASE}/events/upload-image`, {
            method: 'POST',
            body: formData,
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            alert(err.detail || 'Не удалось загрузить изображение');
            return;
        }
        const data = await resp.json();
        urlInput.value = data.url || '';
    }

    async deleteEventItem(id) {
        if (!confirm('Удалить это мероприятие?')) return;
        await fetch(`${API_BASE}/events/${id}`, { method: 'DELETE' });
        await this.loadEvents();
        this.render();
    }

    async saveMenusYaml() {
        const textarea = document.getElementById('menusYamlEditor');
        if (!textarea) return;

        this.menusYamlStatus = 'Сохранение...';
        this.render();

        try {
            const resp = await fetch(`${API_BASE}/content/menus-ru`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: textarea.value }),
            });
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                this.menusYamlStatus = `Ошибка: ${err.detail || 'не удалось сохранить'}`;
                this.render();
                return;
            }
            this.menusYamlContent = textarea.value;
            this.menusYamlStatus = 'Сохранено. Изменения применены сразу.';
            this.render();
        } catch (e) {
            this.menusYamlStatus = 'Ошибка сети при сохранении';
            this.render();
        }
    }

    async saveTextsYaml() {
        const textarea = document.getElementById('textsYamlEditor');
        if (!textarea) return;

        this.textsYamlStatus = 'Сохранение...';
        this.render();

        try {
            const resp = await fetch(`${API_BASE}/content/texts-ru`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: textarea.value }),
            });
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                this.textsYamlStatus = `Ошибка: ${err.detail || 'не удалось сохранить'}`;
                this.render();
                return;
            }
            this.textsYamlContent = textarea.value;
            this.textsYamlStatus = 'Сохранено. Тексты применены сразу.';
            this.render();
        } catch (e) {
            this.textsYamlStatus = 'Ошибка сети при сохранении';
            this.render();
        }
    }

    async saveButtonLabels() {
        const inputs = Array.from(document.querySelectorAll('.button-label-input'));
        if (!inputs.length) return;

        const updates = inputs.map((el) => ({
            path: el.dataset.path,
            label: el.value
        }));

        this.buttonLabelsStatus = 'Сохранение...';
        this.render();

        try {
            const resp = await fetch(`${API_BASE}/content/button-labels`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ updates }),
            });
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                this.buttonLabelsStatus = `Ошибка: ${err.detail || 'не удалось сохранить'}`;
                this.render();
                return;
            }
            this.buttonLabelsStatus = 'Названия кнопок сохранены и применены сразу.';
            await this.loadButtonLabels();
            await this.loadMenusYaml();
            this.render();
        } catch (e) {
            this.buttonLabelsStatus = 'Ошибка сети при сохранении названий кнопок';
            this.render();
        }
    }

    async deleteGuideItem(id) {
        if (!confirm('Удалить это место?')) return;
        await fetch(`${API_BASE}/guide/${id}`, { method: 'DELETE' });
        await this.loadGuide();
        this.render();
    }

    async saveStaff(staffData) {
        const method = staffData.id ? 'PUT' : 'POST';
        const url = staffData.id ? `${API_BASE}/staff/${staffData.id}` : `${API_BASE}/staff`;
        try {
            const resp = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(staffData)
            });
            if (!resp.ok) {
                const err = await resp.json();
                alert(err.detail || 'Ошибка при сохранении');
                return;
            }
            this.editingStaff = null;
            await this.loadStaff();
            this.render();
        } catch (e) {
            console.error(e);
            alert('Ошибка сети');
        }
    }

    async deleteStaff(id) {
        if (!confirm('Удалить этого сотрудника?')) return;
        await fetch(`${API_BASE}/staff/${id}`, { method: 'DELETE' });
        await this.loadStaff();
        this.render();
    }

    async checkAvailability() {
        const ci = document.getElementById('checkIn').value;
        const co = document.getElementById('checkOut').value;
        const ad = document.getElementById('adults').value;
        if (!ci || !co) return alert('Выберите даты');
        try {
            this.availability = 'loading';
            this.render();
            const r = await fetch(`${API_BASE}/shelter/availability?check_in=${ci}&check_out=${co}&adults=${ad}`);
            this.availability = await r.json();
            this.render();
        } catch (e) {
            this.availability = { error: e.message };
            this.render();
        }
    }

    switchTab(tab) {
        this.currentTab = tab;
        this.render();
    }

    render() {
        const app = document.getElementById('app');
        if (this.isUserAdmin) {
            app.innerHTML = this.renderAdminLayout();
            this.renderStatistics();
            this.renderTicketList();
            this.renderTicketDetail();
        } else {
            app.innerHTML = this.renderGuestLayout();
        }
    }

    renderAdminLayout() {
        return `
            <div class="min-h-screen bg-gray-50">
                <header class="bg-green-800 text-white p-6 shadow-lg">
                    <div class="container mx-auto flex justify-between items-center">
                        <div>
                            <h1 class="text-3xl font-bold">🏨 GORA Hotel - Админ Панель</h1>
                            <p class="text-sm opacity-90">Система управления отелем</p>
                        </div>
                        <nav class="flex gap-4 overflow-x-auto">
                            <button onclick="app.switchTab('tickets')" class="px-4 py-2 rounded-lg ${this.currentTab === 'tickets' ? 'bg-green-700 shadow-inner font-bold' : 'hover:bg-green-700'}">Заявки</button>
                            <button onclick="app.switchTab('shelter')" class="px-4 py-2 rounded-lg ${this.currentTab === 'shelter' ? 'bg-green-700 shadow-inner font-bold' : 'hover:bg-green-700'}">Shelter PMS</button>
                            <button onclick="app.switchTab('menu')" class="px-4 py-2 rounded-lg ${this.currentTab === 'menu' ? 'bg-green-700 shadow-inner font-bold' : 'hover:bg-green-700'}">Меню</button>
                            <button onclick="app.switchTab('guide')" class="px-4 py-2 rounded-lg ${this.currentTab === 'guide' ? 'bg-green-700 shadow-inner font-bold' : 'hover:bg-green-700'}">Гид</button>
                            <button onclick="app.switchTab('events')" class="px-4 py-2 rounded-lg ${this.currentTab === 'events' ? 'bg-green-700 shadow-inner font-bold' : 'hover:bg-green-700'}">Мероприятия</button>
                            <button onclick="app.switchTab('staff')" class="px-4 py-2 rounded-lg ${this.currentTab === 'staff' ? 'bg-green-700 shadow-inner font-bold' : 'hover:bg-green-700'}">Задачи</button>
                            <button onclick="app.switchTab('staff_management')" class="px-4 py-2 rounded-lg ${this.currentTab === 'staff_management' ? 'bg-green-700 shadow-inner font-bold' : 'hover:bg-green-700'}">Сотрудники</button>
                            <button onclick="app.switchTab('content_editor')" class="px-4 py-2 rounded-lg ${this.currentTab === 'content_editor' ? 'bg-green-700 shadow-inner font-bold' : 'hover:bg-green-700'}">Контент</button>
                            <button onclick="app.switchTab('cameras')" class="px-4 py-2 rounded-lg ${this.currentTab === 'cameras' ? 'bg-green-700 shadow-inner font-bold' : 'hover:bg-green-700'}">Камеры</button>
                            <button onclick="app.switchTab('marketing')" class="px-4 py-2 rounded-lg ${this.currentTab === 'marketing' ? 'bg-green-700 shadow-inner font-bold' : 'hover:bg-green-700'}">Маркетинг</button>
                        </nav>
                    </div>
                </header>
                <div class="container mx-auto p-6">
                    ${this.currentTab === 'tickets' ? `
                        <div id="statistics"></div>
                        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
                            <div>
                                <div class="mb-4 flex gap-2">
                                    <button onclick="app.loadTickets(null)" class="px-4 py-2 rounded-lg ${this.ticketStatusFilter === null ? 'bg-blue-700 text-white font-bold shadow-inner' : 'bg-blue-600 text-white'}">Все</button>
                                    <button onclick="app.loadTickets('PENDING_ADMIN')" class="px-4 py-2 rounded-lg ${this.ticketStatusFilter === 'PENDING_ADMIN' ? 'bg-orange-700 text-white font-bold shadow-inner' : 'bg-orange-600 text-white'}">Ожидают</button>
                                    <button onclick="app.loadTickets('COMPLETED')" class="px-4 py-2 rounded-lg ${this.ticketStatusFilter === 'COMPLETED' ? 'bg-green-700 text-white font-bold shadow-inner' : 'bg-green-600 text-white'}">Решено</button>
                                </div>
                                <div id="ticketList" class="space-y-4 max-h-screen overflow-y-auto"></div>
                            </div>
                            <div id="ticketDetail"></div>
                        </div>
                    ` : this.renderCurrentTabContent()}
                </div>
            </div>
        `;
    }

    renderCurrentTabContent() {
        switch (this.currentTab) {
            case 'shelter': return this.renderShelterTab();
            case 'menu': return this.renderMenuTab();
            case 'guide': return this.renderGuideTab();
            case 'events': return this.renderEventsTab();
            case 'staff': return this.renderStaffTab();
            case 'staff_management': return this.renderStaffManagementTab();
            case 'content_editor': return this.renderContentEditorTab();
            case 'cameras': return this.renderCamerasTab();
            case 'marketing': return this.renderMarketingTab();
            default: return '';
        }
    }

    renderStatistics() {
        const container = document.getElementById('statistics');
        if (!container || !this.stats) return;
        container.innerHTML = `
            <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
                <div class="bg-white p-4 rounded-xl shadow border-b-4 border-blue-500">
                    <div class="text-xs text-gray-500 font-bold uppercase">Заявок сегодня</div>
                    <div class="text-2xl font-black text-blue-600">${this.stats.total_tickets_today}</div>
                </div>
                <div class="bg-white p-4 rounded-xl shadow border-b-4 border-orange-500">
                    <div class="text-xs text-gray-500 font-bold uppercase">Ожидают</div>
                    <div class="text-2xl font-black text-orange-600">${this.stats.pending_tickets}</div>
                </div>
                <div class="bg-white p-4 rounded-xl shadow border-b-4 border-green-500">
                    <div class="text-xs text-gray-500 font-bold uppercase">Решено</div>
                    <div class="text-2xl font-black text-green-600">${this.stats.completed_today}</div>
                </div>
                <div class="bg-white p-4 rounded-xl shadow border-b-4 border-red-500">
                    <div class="text-xs text-gray-500 font-bold uppercase">Отклонено</div>
                    <div class="text-2xl font-black text-red-600">${this.stats.declined_today}</div>
                </div>
                <div class="bg-white p-4 rounded-xl shadow border-b-4 border-purple-500">
                    <div class="text-xs text-gray-500 font-bold uppercase">Активных</div>
                    <div class="text-2xl font-black text-purple-600">${this.stats.total_active}</div>
                </div>
            </div>
        `;
    }

    async deleteTicket(id, event) {
        if (event) {
            event.stopPropagation();
        }
        if (!confirm('Вы уверены, что хотите удалить эту заявку? Это действие нельзя отменить.')) return;
        
        try {
            await fetch(`${API_BASE}/tickets/${id}`, { method: 'DELETE' });
            if (this.currentTicket && this.currentTicket.id === id) {
                this.currentTicket = null;
            }
            await this.loadTickets();
            await this.loadStatistics();
        } catch (e) {
            console.error('Failed to delete ticket', e);
        }
    }

    renderTicketList() {
        const container = document.getElementById('ticketList');
        if (!container) return;
        const colors = { 'NEW': 'bg-blue-100 text-blue-800', 'PENDING_ADMIN': 'bg-orange-100 text-orange-800', 'COMPLETED': 'bg-green-100 text-green-800', 'DECLINED': 'bg-red-100 text-red-800' };
        const selectedTicketId = this.currentTicket?.id;
        container.innerHTML = this.tickets.map(t => `
            <div onclick="app.loadTicketDetail(${t.id})" class="bg-white p-4 rounded-xl shadow hover:shadow-md cursor-pointer border-l-4 transition relative group ${selectedTicketId === t.id ? 'ring-2 ring-blue-200 border-blue-500' : t.has_new_guest_message ? 'border-amber-500 bg-amber-50/40' : t.status === 'PENDING_ADMIN' ? 'border-orange-500' : 'border-gray-200'}">
                <button onclick="app.deleteTicket(${t.id}, event)" class="absolute top-2 right-2 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-full w-6 h-6 flex items-center justify-center transition-colors hidden group-hover:flex" title="Удалить заявку">✕</button>
                <div class="flex justify-between items-start pr-6">
                    <div class="font-bold text-lg">Заявка #${t.id}</div>
                    <div class="flex items-center gap-2">
                        ${t.has_new_guest_message ? `<span class="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded-full font-bold bg-amber-100 text-amber-800">🔔 ${t.new_guest_messages_count}</span>` : ''}
                        <span class="text-[10px] px-2 py-1 rounded-full font-bold ${colors[t.status] || 'bg-gray-100'}">${t.status}</span>
                    </div>
                </div>
                <div class="text-sm text-gray-600 mt-2">
                    <div>👤 ${this.escapeHtml(t.guest_name || t.guest_chat_id)}</div>
                    <div class="flex items-center justify-between gap-2 text-[10px] mt-1">
                        <span class="text-gray-400">🕐 ${new Date(t.last_message_at || t.updated_at || t.created_at).toLocaleString('ru-RU')}</span>
                        ${t.has_new_guest_message ? '<span class="font-semibold text-amber-700">Новое сообщение гостя</span>' : ''}
                    </div>
                </div>
            </div>
        `).join('') || '<div class="text-center text-gray-400 py-10">Нет заявок</div>';
    }

    renderTicketDetail() {
        const container = document.getElementById('ticketDetail');
        if (!container) return;
        if (!this.currentTicket) { container.innerHTML = '<div class="bg-white p-10 rounded-xl shadow text-center text-gray-400 font-medium">Выберите заявку из списка слева</div>'; return; }
        const t = this.currentTicket;
        const msgs = t.messages.map(m => `
            <div class="p-3 rounded-2xl ${m.sender === 'ADMIN' ? 'bg-blue-50 ml-8' : m.sender === 'SYSTEM' ? 'bg-slate-50 border border-slate-200 mx-4' : 'bg-gray-100 mr-8'} mb-3">
                <div class="flex items-center gap-2 mb-1 text-[10px] font-bold text-gray-500">
                    <span>${m.sender === 'ADMIN' ? '👨‍💼 ' + (m.admin_name || 'Админ') : m.sender === 'SYSTEM' ? '⚙️ Система' : '👤 Гость'}</span>
                    <span>•</span>
                    <span>${new Date(m.created_at).toLocaleTimeString('ru-RU')}</span>
                </div>
                <div class="text-sm">${this.escapeHtml(m.content)}</div>
            </div>
        `).join('');
        container.innerHTML = `
            <div class="bg-white p-6 rounded-xl shadow-lg sticky top-6">
                <div class="flex justify-between items-center mb-6 border-b pb-4">
                    <h2 class="text-2xl font-black">Заявка #${t.id}</h2>
                    <button onclick="app.currentTicket = null; app.render()" class="text-gray-400 hover:text-gray-600 text-2xl">✕</button>
                </div>
                <div class="mb-3 text-sm ${t.dialog_open ? 'text-green-700' : 'text-gray-500'}">
                    💬 Диалог: <b>${t.dialog_open ? 'Открыт' : 'Закрыт'}</b>
                    ${t.dialog_expires_at ? ` · до ${new Date(t.dialog_expires_at).toLocaleString('ru-RU')}` : ''}
                </div>
                ${t.has_new_guest_message ? `<div class="mb-3 inline-flex items-center gap-2 px-3 py-2 rounded-full bg-amber-100 text-amber-800 text-xs font-bold">🔔 Новые сообщения от гостя: ${t.new_guest_messages_count}</div>` : ''}
                <div id="ticketMessagesContainer" class="max-h-[400px] overflow-y-auto mb-6 px-2">${msgs}</div>
                ${(t.status === 'NEW' || t.status === 'PENDING_ADMIN') ? `
                    <div class="space-y-3">
                        <textarea id="messageInput" oninput="app.messageDraft = this.value" class="w-full border-2 border-gray-100 rounded-2xl p-4 text-sm focus:border-blue-500 outline-none transition h-32" placeholder="Напишите ответ гостю..."></textarea>
                        <div class="flex gap-2">
                            <button onclick="app.handleSendMessage()" class="flex-1 bg-blue-600 text-white font-bold py-3 rounded-xl hover:bg-blue-700 transition">Отправить</button>
                            <button onclick="app.closeDialog(${t.id})" class="bg-slate-600 text-white font-bold px-4 rounded-xl hover:bg-slate-700 transition">🔒 Закрыть диалог</button>
                            <button onclick="app.updateTicketStatus(${t.id}, 'COMPLETED')" class="bg-green-600 text-white font-bold px-6 rounded-xl hover:bg-green-700 transition">✅ Выполнено</button>
                            <button onclick="app.updateTicketStatus(${t.id}, 'DECLINED')" class="bg-red-500 text-white font-bold px-6 rounded-xl hover:bg-red-600 transition">❌ Отклонить</button>
                        </div>
                        <div class="border-t pt-4 mt-2">
                            <div class="font-bold mb-2">Назначить поручение сотруднику</div>
                            <div class="grid grid-cols-1 gap-2">
                                <select id="ticketAssignee" class="w-full border p-2 rounded-lg">
                                    ${this.getStaffOptionsHtml()}
                                </select>
                                <select id="ticketTaskType" class="w-full border p-2 rounded-lg">
                                    <option value="Уборка">Уборка</option>
                                    <option value="Техническая задача">Техническая задача</option>
                                    <option value="Доставка">Доставка</option>
                                    <option value="Прочее">Прочее</option>
                                </select>
                                <textarea id="ticketTaskDesc" class="w-full border p-3 rounded-lg text-sm h-20" placeholder="Описание поручения для сотрудника"></textarea>
                                <button onclick="app.createStaffTaskFromCurrentTicket()" class="bg-purple-600 text-white font-bold py-2 rounded-xl hover:bg-purple-700 transition">Создать поручение</button>
                            </div>
                        </div>
                    </div>
                ` : `<div class="text-center p-4 bg-gray-50 rounded-xl text-gray-500 font-bold">Заявка закрыта со статусом: ${t.status}</div>`}
            </div>
        `;
    }

    async sendMessage(ticketId, content) {
        let adminId = null, adminName = null;
        if (window.Telegram?.WebApp?.initDataUnsafe?.user) {
            const u = window.Telegram.WebApp.initDataUnsafe.user;
            adminId = u.id.toString(); adminName = u.first_name + (u.last_name ? ' ' + u.last_name : '');
        }
        const r = await fetch(`${API_BASE}/tickets/${ticketId}/messages`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content, admin_telegram_id: adminId, admin_name: adminName })
        });
        if (r.ok) {
            this.messageDraft = '';
            await this.loadTicketDetail(ticketId);
            await this.loadTickets();
        }
    }

    async updateTicketStatus(id, status) {
        const r = await fetch(`${API_BASE}/tickets/${id}/status`, {
            method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status })
        });
        if (r.ok) { await this.loadTicketDetail(id); await this.loadTickets(); await this.loadStatistics(); }
    }

    async closeDialog(id) {
        const r = await fetch(`${API_BASE}/tickets/${id}/dialog/close`, { method: 'POST' });
        if (r.ok) {
            await this.loadTicketDetail(id);
            await this.loadTickets();
            await this.loadStatistics();
        }
    }

    handleSendMessage() {
        const input = document.getElementById('messageInput');
        if (input?.value.trim() && this.currentTicket) {
            this.messageDraft = '';
            this.sendMessage(this.currentTicket.id, input.value.trim());
            input.value = '';
        }
    }

    getStaffOptionsHtml() {
        const activeStaff = (this.staff || []).filter(s => s.is_active);
        if (!activeStaff.length) {
            return `<option value="">Нет активных сотрудников</option>`;
        }
        return [
            `<option value="">Выберите ответственного</option>`,
            ...activeStaff.map(s => `<option value="${s.id}">${this.escapeHtml(s.full_name)}${s.telegram_id ? '' : ' (без Telegram)'}</option>`)
        ].join('');
    }

    async createStaffTaskFromCurrentTicket() {
        if (!this.currentTicket) return;
        const assignee = document.getElementById('ticketAssignee')?.value || '';
        const taskType = document.getElementById('ticketTaskType')?.value || 'Прочее';
        const description = document.getElementById('ticketTaskDesc')?.value?.trim() || '';

        if (!assignee) {
            alert('Выберите ответственного сотрудника');
            return;
        }

        const room = this.currentTicket.room_number || 'Не указан';
        const payload = {
            room_number: room,
            task_type: taskType,
            description: description || `Поручение по заявке #${this.currentTicket.id}`,
            assigned_to: assignee,
        };

        const resp = await fetch(`${API_BASE}/staff/tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            alert(err.detail || 'Не удалось создать поручение');
            return;
        }

        await this.loadStaffTasks();
        alert('Поручение создано и отправлено сотруднику (если у него есть Telegram ID).');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    renderShelterTab() {
        if (!this.hotelParams) return '<div class="text-center py-20">Загрузка...</div>';
        const h = this.hotelParams;
        const categoriesHTML = (h.categories || []).map(cat => `<div class="bg-white p-4 rounded-lg shadow border-l-4 border-blue-500"><div class="font-bold text-lg mb-1">${cat.name}</div><div class="text-sm text-gray-600">ID: ${cat.id}</div></div>`).join('');
        const amenitiesHTML = (h.amenities || []).map(a => `<div class="flex items-center gap-2 bg-gray-100 px-3 py-1 rounded-full text-sm"><span>🔹</span> ${a.name}</div>`).join('');
        const ratesHTML = (h.rates || []).map(r => `<div class="bg-white p-4 rounded-lg shadow border-l-4 border-purple-500"><div class="font-bold text-lg mb-1">${r.name}</div><div class="text-sm text-gray-600">ID: ${r.id}</div></div>`).join('');
        return `
            <div class="space-y-8">
                <section>
                    <h2 class="text-2xl font-bold mb-4">🏨 Информация об отеле</h2>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div class="bg-white p-6 rounded-xl shadow-md border-t-4 border-green-600">
                            <div class="space-y-3">
                                <div class="flex justify-between border-b pb-2"><span>Название:</span> <span class="font-semibold">${h.hotel_info.hotelName || 'Отель Гора'}</span></div>
                                <div class="flex justify-between border-b pb-2"><span>ID Отеля:</span> <span class="font-semibold">${h.hotel_info.hotelId || 'N/A'}</span></div>
                                <div class="flex justify-between border-b pb-2"><span>Город:</span> <span class="font-semibold">${h.hotel_info.hotelCity || 'Сортавала'}</span></div>
                            </div>
                        </div>
                        <div class="bg-white p-6 rounded-xl shadow-md border-t-4 border-blue-600">
                            <div class="space-y-3">
                                <div class="flex justify-between border-b pb-2"><span>Макс. гостей:</span> <span class="font-semibold">${h.settings.maxRoomCapacity || '6'}</span></div>
                                <div class="flex justify-between border-b pb-2"><span>Доп. услуги:</span> <span class="font-semibold">${h.settings.allowUpsale ? '✅ Включены' : '❌ Выключены'}</span></div>
                            </div>
                        </div>
                    </div>
                </section>
                <section class="bg-blue-50 p-6 rounded-2xl border-2 border-blue-200">
                    <h2 class="text-2xl font-bold mb-4">🔍 Живой поиск номеров</h2>
                    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
                        <input type="date" id="checkIn" class="border rounded-lg p-2" value="${new Date().toISOString().split('T')[0]}">
                        <input type="date" id="checkOut" class="border rounded-lg p-2" value="${new Date(Date.now() + 86400000).toISOString().split('T')[0]}">
                        <select id="adults" class="border rounded-lg p-2"><option value="2">2 чел</option><option value="1">1 чел</option></select>
                        <button onclick="app.checkAvailability()" class="bg-blue-600 text-white px-6 py-2 rounded-lg font-bold">Найти</button>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
                        ${Array.isArray(this.availability) ? this.availability.map(v => `
                            <div class="bg-white p-4 rounded-xl shadow border">
                                <div class="font-bold">${v.category_name}</div>
                                <div class="text-xl font-black text-green-600 mt-2">${v.price} ₽</div>
                                <div class="text-xs text-gray-400 mt-1">Осталось: ${v.available_count}</div>
                            </div>
                        `).join('') : (this.availability === 'loading' ? 'Поиск...' : '')}
                    </div>
                </section>
                <section><h2 class="text-2xl font-bold mb-4">✨ Удобства</h2><div class="flex flex-wrap gap-3">${amenitiesHTML}</div></section>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <section><h2 class="text-2xl font-bold mb-4">🛌 Категории</h2><div class="grid grid-cols-1 gap-4">${categoriesHTML}</div></section>
                    <section><h2 class="text-2xl font-bold mb-4">💰 Тарифы</h2><div class="grid grid-cols-1 gap-4">${ratesHTML}</div></section>
                </div>
            </div>
        `;
    }

    renderMenuTab() {
        const categories = { breakfast: '🍳 Завтрак', lunch: '🍽 Обед', dinner: '🌙 Ужин' };
        return `
            <div class="space-y-6">
                <div class="flex justify-between items-center">
                    <h2 class="text-2xl font-bold">🍽 Редактор меню</h2>
                    <button onclick="app.editingMenuItem = {category: 'breakfast', category_type: 'breakfast', name: '', price: 0, composition: [], is_available: true}; app.render()" class="bg-green-600 text-white px-6 py-2 rounded-lg font-bold">+ Добавить блюдо</button>
                </div>

                <div class="bg-white p-4 rounded-xl shadow border">
                    <h3 class="text-lg font-bold mb-3">Доступность категорий для гостей</h3>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                        ${Object.entries(categories).map(([cat, label]) => `
                            <button
                                onclick="app.toggleMenuCategory('${cat}')"
                                class="p-3 rounded-lg border text-left ${this.menuCategorySettings?.[cat] ? 'bg-green-50 border-green-300' : 'bg-gray-50 border-gray-200'}"
                            >
                                <div class="font-semibold">${label}</div>
                                <div class="text-xs mt-1 ${this.menuCategorySettings?.[cat] ? 'text-green-700' : 'text-gray-500'}">
                                    ${this.menuCategorySettings?.[cat] ? 'Включено' : 'Выключено'}
                                </div>
                            </button>
                        `).join('')}
                    </div>
                </div>
                
                ${this.editingMenuItem ? this.renderMenuEditForm() : ''}
                
                ${Object.entries(categories).map(([cat, label]) => `
                    <div class="bg-white p-6 rounded-xl shadow">
                        <h3 class="text-xl font-bold mb-4">${label}</h3>
                        <div class="space-y-3">
                            ${this.menu.filter(m => m.category === cat || m.category_type === cat).map(m => {
            // Format composition for display
            let compStr = '';
            if (Array.isArray(m.composition) && m.composition.length > 0) {
                compStr = m.composition.map(c => {
                    return c.quantity && c.unit ? `${c.name} (${c.quantity} ${c.unit})` : c.name;
                }).join(', ');
            } else if (typeof m.composition === 'string' && m.composition) {
                compStr = m.composition;
            }
            return `
                                <div class="flex items-center justify-between p-4 bg-gray-50 rounded-lg border ${!m.is_available ? 'opacity-50' : ''}">
                                    <div class="flex-1">
                                        <div class="font-bold">${m.name}</div>
                                        <div class="text-sm text-gray-500">${m.price}₽</div>
                                        ${compStr ? `<div class="text-xs text-gray-400 mt-1">🥘 ${compStr}</div>` : ''}
                                        ${m.admin_comment ? `<div class="text-xs text-blue-500 mt-1">💬 ${m.admin_comment}</div>` : ''}
                                    </div>
                                    <div class="flex gap-2">
                                        <button onclick="app.toggleMenuItem(${m.id})" class="px-3 py-1 rounded ${m.is_available ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}">
                                            ${m.is_available ? '✅' : '❌'}
                                        </button>
                                        <button onclick="app.editingMenuItem = {...app.menu.find(x => x.id === ${m.id})}; app.render()" class="bg-blue-100 text-blue-700 px-3 py-1 rounded">✏️</button>
                                        <button onclick="app.deleteMenuItem(${m.id})" class="bg-red-100 text-red-700 px-3 py-1 rounded">🗑</button>
                                    </div>
                                </div>
                            `}).join('') || '<div class="text-gray-400 text-center py-4">Нет блюд в этой категории</div>'}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    renderMenuEditForm() {
        const m = this.editingMenuItem;
        // Parse composition as JSON array or convert from legacy string
        let compositionItems = [];
        if (Array.isArray(m.composition)) {
            compositionItems = m.composition;
        } else if (typeof m.composition === 'string' && m.composition) {
            // Legacy format: convert comma-separated string to objects
            compositionItems = m.composition.split(/[,\n]/).map(s => s.trim()).filter(s => s).map(name => ({ name, quantity: null, unit: null }));
        }
        this.tempCompositionItems = compositionItems;

        const compositionListHTML = compositionItems.map((item, idx) => {
            const qtyUnit = item.quantity && item.unit ? ` - ${item.quantity} ${item.unit}` : '';
            return `
                <div class="flex items-center gap-2 bg-white p-2 rounded border mb-1">
                    <span class="flex-1"><b>${item.name}</b>${qtyUnit}</span>
                    <button onclick="app.removeCompositionItem(${idx})" class="text-red-500 hover:bg-red-100 px-2 py-1 rounded">✕</button>
                </div>
            `;
        }).join('') || '<div class="text-gray-400 text-sm">Нет ингредиентов</div>';

        return `
            <div class="bg-blue-50 p-6 rounded-xl border-2 border-blue-200 mb-6">
                <h3 class="text-lg font-bold mb-4">${m.id ? 'Редактировать блюдо' : 'Новое блюдо'}</h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label class="block text-sm font-bold mb-1">Название блюда</label>
                        <input id="menuName" class="w-full border p-2 rounded" value="${m.name || ''}">
                    </div>
                    <div>
                        <label class="block text-sm font-bold mb-1">Цена (₽)</label>
                        <input id="menuPrice" type="number" class="w-full border p-2 rounded" value="${m.price || 0}">
                    </div>
                    <div>
                        <label class="block text-sm font-bold mb-1">Категория</label>
                        <select id="menuCategory" class="w-full border p-2 rounded">
                            <option value="breakfast" ${m.category_type === 'breakfast' ? 'selected' : ''}>Завтрак</option>
                            <option value="lunch" ${m.category_type === 'lunch' ? 'selected' : ''}>Обед</option>
                            <option value="dinner" ${m.category_type === 'dinner' ? 'selected' : ''}>Ужин</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm font-bold mb-1">Описание</label>
                        <input id="menuDesc" class="w-full border p-2 rounded" value="${m.description || ''}">
                    </div>
                    <div class="md:col-span-2">
                        <label class="block text-sm font-bold mb-2">Состав (ингредиенты с количеством)</label>
                        <div id="compositionList" class="mb-3 max-h-40 overflow-y-auto">
                            ${compositionListHTML}
                        </div>
                        <div class="grid grid-cols-6 gap-2">
                            <input id="newIngredientName" class="col-span-3 border p-2 rounded" placeholder="Название (напр. Яйца)">
                            <input id="newIngredientQty" type="number" class="col-span-1 border p-2 rounded" placeholder="Кол-во">
                            <input id="newIngredientUnit" class="col-span-1 border p-2 rounded" placeholder="шт/мл/г">
                            <button onclick="app.addCompositionItem()" class="col-span-1 bg-green-100 text-green-700 px-3 py-2 rounded font-bold">+</button>
                        </div>
                        <div class="text-xs text-gray-500 mt-1">Пример: "Яйца", "2", "шт" → "Яйца - 2 шт"</div>
                    </div>
                    <div class="md:col-span-2">
                        <label class="block text-sm font-bold mb-1">Комментарий для гостя</label>
                        <input id="menuComment" class="w-full border p-2 rounded" value="${m.admin_comment || ''}" placeholder="Например: Рекомендуем попробовать!">
                    </div>
                </div>
                <div class="flex gap-2 mt-4">
                    <button onclick="app.saveMenuItemWithComposition()" class="bg-green-600 text-white px-6 py-2 rounded-lg font-bold">Сохранить</button>
                    <button onclick="app.editingMenuItem = null; app.tempCompositionItems = []; app.render()" class="border px-6 py-2 rounded-lg">Отмена</button>
                </div>
            </div>
        `;
    }
    renderGuideTab() {
        const categories = { nature: '🌲 Природа и Парки', cafes: '☕ Кафе и Рестораны', rent: '🚤 Активности' };
        return `
            <div class="space-y-6">
                <div class="flex justify-between items-center">
                    <h2 class="text-2xl font-bold">🗺 Редактор гида</h2>
                    <button onclick="app.editingGuideItem = {category: 'nature', name: '', description: '', map_url: ''}; app.render()" class="bg-green-600 text-white px-6 py-2 rounded-lg font-bold">+ Добавить место</button>
                </div>
                
                ${this.editingGuideItem ? this.renderGuideEditForm() : ''}
                
                ${Object.entries(categories).map(([cat, label]) => `
                    <div class="bg-white p-6 rounded-xl shadow">
                        <h3 class="text-xl font-bold mb-4">${label}</h3>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            ${this.guide.filter(g => g.category === cat).map(g => `
                                <div class="p-4 bg-gray-50 rounded-lg border">
                                    <div class="flex justify-between items-start">
                                        <div class="flex-1">
                                            <div class="font-bold text-lg">${g.name}</div>
                                            <div class="text-sm text-gray-600 mt-1">${g.description}</div>
                                            ${g.map_url ? `<a href="${g.map_url}" target="_blank" class="text-blue-600 text-sm mt-2 inline-block">📍 На карте</a>` : ''}
                                        </div>
                                        <div class="flex gap-2">
                                            <button onclick="app.editingGuideItem = {...app.guide.find(x => x.id === ${g.id})}; app.render()" class="bg-blue-100 text-blue-700 px-3 py-1 rounded">✏️</button>
                                            <button onclick="app.deleteGuideItem(${g.id})" class="bg-red-100 text-red-700 px-3 py-1 rounded">🗑</button>
                                        </div>
                                    </div>
                                </div>
                            `).join('') || '<div class="text-gray-400 text-center py-4 col-span-2">Нет мест в этой категории</div>'}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    renderGuideEditForm() {
        const g = this.editingGuideItem;
        return `
            <div class="bg-blue-50 p-6 rounded-xl border-2 border-blue-200 mb-6">
                <h3 class="text-lg font-bold mb-4">${g.id ? 'Редактировать место' : 'Новое место'}</h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label class="block text-sm font-bold mb-1">Название</label>
                        <input id="guideName" class="w-full border p-2 rounded" value="${g.name || ''}">
                    </div>
                    <div>
                        <label class="block text-sm font-bold mb-1">Категория</label>
                        <select id="guideCategory" class="w-full border p-2 rounded">
                            <option value="nature" ${g.category === 'nature' ? 'selected' : ''}>Природа</option>
                            <option value="cafes" ${g.category === 'cafes' ? 'selected' : ''}>Кафе</option>
                            <option value="rent" ${g.category === 'rent' ? 'selected' : ''}>Активности</option>
                        </select>
                    </div>
                    <div class="md:col-span-2">
                        <label class="block text-sm font-bold mb-1">Описание</label>
                        <textarea id="guideDesc" class="w-full border p-2 rounded h-24">${g.description || ''}</textarea>
                    </div>
                    <div class="md:col-span-2">
                        <label class="block text-sm font-bold mb-1">Ссылка на карту (Google Maps / Яндекс)</label>
                        <input id="guideMapUrl" class="w-full border p-2 rounded" value="${g.map_url || ''}" placeholder="https://maps.google.com/...">
                    </div>
                    <div class="md:col-span-2">
                        <label class="block text-sm font-bold mb-1">Ссылка на изображение</label>
                        <input id="guideImageUrl" class="w-full border p-2 rounded" value="${g.image_url || ''}" placeholder="https://...">
                    </div>
                </div>
                <div class="flex gap-2 mt-4">
                    <button onclick="app.saveGuideItem({
                        id: ${g.id || 'null'},
                        name: document.getElementById('guideName').value,
                        category: document.getElementById('guideCategory').value,
                        description: document.getElementById('guideDesc').value,
                        map_url: document.getElementById('guideMapUrl').value,
                        image_url: document.getElementById('guideImageUrl').value
                    })" class="bg-green-600 text-white px-6 py-2 rounded-lg font-bold">Сохранить</button>
                    <button onclick="app.editingGuideItem = null; app.render()" class="border px-6 py-2 rounded-lg">Отмена</button>
                </div>
            </div>
        `;
    }

    renderEventsTab() {
        return `
            <div class="space-y-6">
                <div class="flex justify-between items-center">
                    <h2 class="text-2xl font-bold">🎉 Мероприятия</h2>
                    <button onclick="app.editingEventItem = {name: '', description: '', location_text: '', map_url: '', image_url: '', starts_at: '', ends_at: '', publish_from: '', publish_until: '', is_active: true}; app.render()" class="bg-green-600 text-white px-6 py-2 rounded-lg font-bold">+ Добавить мероприятие</button>
                </div>

                ${this.editingEventItem ? this.renderEventEditForm() : ''}

                <div class="bg-white p-6 rounded-xl shadow">
                    <div class="space-y-4">
                        ${(this.events || []).map((e) => `
                            <div class="p-4 bg-gray-50 rounded-lg border ${!e.is_active ? 'opacity-60' : ''}">
                                <div class="flex justify-between items-start gap-3">
                                    <div class="flex-1">
                                        <div class="font-bold text-lg">${this.escapeHtml(e.name || '')}</div>
                                        <div class="text-sm text-gray-600 mt-1">${this.escapeHtml(e.description || '')}</div>
                                        <div class="text-xs text-gray-500 mt-2">
                                            Проведение: ${new Date(e.starts_at).toLocaleString('ru-RU')} — ${new Date(e.ends_at).toLocaleString('ru-RU')}
                                        </div>
                                        <div class="text-xs text-gray-500 mt-1">
                                            Показ объявления: ${new Date(e.publish_from || e.starts_at).toLocaleString('ru-RU')} — ${new Date(e.publish_until || e.ends_at).toLocaleString('ru-RU')}
                                        </div>
                                        ${e.location_text ? `<div class="text-xs text-gray-500 mt-1">📍 ${this.escapeHtml(e.location_text)}</div>` : ''}
                                        ${e.map_url ? `<a class="text-xs text-blue-600 mt-1 inline-block" target="_blank" href="${this.escapeHtml(e.map_url)}">Открыть карту</a>` : ''}
                                    </div>
                                    <div class="flex gap-2">
                                        <button onclick="app.editingEventItem = {...app.events.find(x => x.id === ${e.id})}; app.render()" class="bg-blue-100 text-blue-700 px-3 py-1 rounded">✏️</button>
                                        <button onclick="app.deleteEventItem(${e.id})" class="bg-red-100 text-red-700 px-3 py-1 rounded">🗑</button>
                                    </div>
                                </div>
                            </div>
                        `).join('') || '<div class="text-gray-400 text-center py-6">Нет мероприятий</div>'}
                    </div>
                </div>
            </div>
        `;
    }

    renderEventEditForm() {
        const e = this.editingEventItem || {};
        const nowLocal = new Date(Date.now() - (new Date().getTimezoneOffset() * 60000)).toISOString().slice(0, 16);
        const startsValue = e.starts_at ? String(e.starts_at).slice(0, 16) : '';
        const endsValue = e.ends_at ? String(e.ends_at).slice(0, 16) : '';
        const publishFromValue = e.publish_from ? String(e.publish_from).slice(0, 16) : (e.id ? startsValue : nowLocal);
        const publishUntilValue = e.publish_until ? String(e.publish_until).slice(0, 16) : endsValue;
        return `
            <div class="bg-blue-50 p-6 rounded-xl border-2 border-blue-200 mb-6">
                <h3 class="text-lg font-bold mb-4">${e.id ? 'Редактировать мероприятие' : 'Новое мероприятие'}</h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label class="block text-sm font-bold mb-1">Название</label>
                        <input id="eventName" class="w-full border p-2 rounded" value="${this.escapeHtml(e.name || '')}">
                    </div>
                    <div>
                        <label class="block text-sm font-bold mb-1">Место проведения</label>
                        <input id="eventLocation" class="w-full border p-2 rounded" value="${this.escapeHtml(e.location_text || '')}">
                    </div>
                    <div class="md:col-span-2">
                        <label class="block text-sm font-bold mb-1">Описание</label>
                        <textarea id="eventDescription" class="w-full border p-2 rounded h-24">${this.escapeHtml(e.description || '')}</textarea>
                    </div>
                    <div>
                        <label class="block text-sm font-bold mb-1">Начало проведения</label>
                        <input id="eventStartsAt" type="datetime-local" class="w-full border p-2 rounded" value="${startsValue}">
                    </div>
                    <div>
                        <label class="block text-sm font-bold mb-1">Окончание проведения</label>
                        <input id="eventEndsAt" type="datetime-local" class="w-full border p-2 rounded" value="${endsValue}">
                    </div>
                    <div>
                        <label class="block text-sm font-bold mb-1">Показывать объявление с</label>
                        <input id="eventPublishFrom" type="datetime-local" class="w-full border p-2 rounded" value="${publishFromValue}">
                    </div>
                    <div>
                        <label class="block text-sm font-bold mb-1">Показывать объявление до</label>
                        <input id="eventPublishUntil" type="datetime-local" class="w-full border p-2 rounded" value="${publishUntilValue}">
                    </div>
                    <div>
                        <label class="block text-sm font-bold mb-1">Ссылка/координаты</label>
                        <input id="eventMapUrl" class="w-full border p-2 rounded" value="${this.escapeHtml(e.map_url || '')}">
                    </div>
                    <div class="md:col-span-2">
                        <label class="block text-sm font-bold mb-1">Фото мероприятия (файл)</label>
                        <div class="flex gap-2">
                            <input id="eventImageFile" type="file" accept="image/*" class="w-full border p-2 rounded bg-white">
                            <button type="button" onclick="app.uploadEventImage()" class="bg-blue-600 text-white px-4 rounded">Загрузить</button>
                        </div>
                        <input id="eventImageUrl" class="w-full border p-2 rounded mt-2 bg-gray-100" value="${this.escapeHtml(e.image_url || '')}" readonly>
                        <div class="text-xs text-gray-500 mt-1">После загрузки URL подставится автоматически.</div>
                    </div>
                    <div class="md:col-span-2">
                        <label class="flex items-center gap-2">
                            <input id="eventIsActive" type="checkbox" ${e.is_active === false ? '' : 'checked'}>
                            <span>Активно</span>
                        </label>
                    </div>
                </div>
                <div class="flex gap-2 mt-4">
                    <button onclick="app.saveEventItem({
                        id: ${e.id || 'null'},
                        name: document.getElementById('eventName').value.trim(),
                        description: document.getElementById('eventDescription').value.trim(),
                        location_text: document.getElementById('eventLocation').value.trim(),
                        map_url: document.getElementById('eventMapUrl').value.trim(),
                        image_url: document.getElementById('eventImageUrl').value.trim(),
                        starts_at: document.getElementById('eventStartsAt').value,
                        ends_at: document.getElementById('eventEndsAt').value,
                        publish_from: document.getElementById('eventPublishFrom').value,
                        publish_until: document.getElementById('eventPublishUntil').value,
                        is_active: document.getElementById('eventIsActive').checked
                    })" class="bg-green-600 text-white px-6 py-2 rounded-lg font-bold">Сохранить</button>
                    <button onclick="app.editingEventItem = null; app.render()" class="border px-6 py-2 rounded-lg">Отмена</button>
                </div>
            </div>
        `;
    }

    renderStaffManagementTab() {
        const roles = { maid: '🧹 Горничная', technician: '🔧 Тех. специалист', administrator: '👨‍💼 Администратор' };
        return `
            <div class="space-y-6">
                <div class="flex justify-between items-center">
                    <h2 class="text-2xl font-bold">👥 Управление сотрудниками</h2>
                    <button onclick="app.editingStaff = {full_name: '', phone: '', telegram_id: '', role: 'maid', permissions: {edit_menu: false, edit_guide: false, view_tickets: true}}; app.render()" class="bg-green-600 text-white px-6 py-2 rounded-lg font-bold">+ Добавить сотрудника</button>
                </div>
                
                ${this.editingStaff ? this.renderStaffEditForm() : ''}
                
                <div class="bg-white p-6 rounded-xl shadow">
                    <div class="space-y-4">
                        ${this.staff.map(s => `
                            <div class="flex items-center justify-between p-4 bg-gray-50 rounded-lg border ${!s.is_active ? 'opacity-50' : ''}">
                                <div class="flex-1">
                                    <div class="font-bold">${s.full_name}</div>
                                    <div class="text-sm text-gray-500">${roles[s.role] || s.role}</div>
                                    <div class="text-xs text-gray-400">📱 ${s.phone}${s.telegram_id ? ' | TG: ' + s.telegram_id : ''}</div>
                                    <div class="text-xs mt-1">
                                        ${s.permissions?.edit_menu ? '<span class="bg-blue-100 text-blue-700 px-2 py-0.5 rounded mr-1">Меню</span>' : ''}
                                        ${s.permissions?.edit_guide ? '<span class="bg-green-100 text-green-700 px-2 py-0.5 rounded mr-1">Гид</span>' : ''}
                                        ${s.permissions?.view_tickets ? '<span class="bg-orange-100 text-orange-700 px-2 py-0.5 rounded mr-1">Заявки</span>' : ''}
                                    </div>
                                </div>
                                <div class="flex gap-2">
                                    <button onclick="app.editingStaff = {...app.staff.find(x => x.id === ${s.id})}; app.render()" class="bg-blue-100 text-blue-700 px-3 py-1 rounded">✏️</button>
                                    <button onclick="app.deleteStaff(${s.id})" class="bg-red-100 text-red-700 px-3 py-1 rounded">🗑</button>
                                </div>
                            </div>
                        `).join('') || '<div class="text-gray-400 text-center py-8">Нет сотрудников</div>'}
                    </div>
                </div>
            </div>
        `;
    }

    renderStaffEditForm() {
        const s = this.editingStaff;
        const perms = s.permissions || {};
        return `
            <div class="bg-blue-50 p-6 rounded-xl border-2 border-blue-200 mb-6">
                <h3 class="text-lg font-bold mb-4">${s.id ? 'Редактировать сотрудника' : 'Новый сотрудник'}</h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label class="block text-sm font-bold mb-1">ФИО <span class="text-red-500">*</span></label>
                        <input id="staffName" class="w-full border p-2 rounded" value="${s.full_name || ''}" required>
                    </div>
                    <div>
                        <label class="block text-sm font-bold mb-1">Телефон <span class="text-red-500">*</span></label>
                        <input id="staffPhone" class="w-full border p-2 rounded" value="${s.phone || ''}" placeholder="+7XXXXXXXXXX" required>
                        <div class="text-xs text-gray-500 mt-1">Основной идентификатор сотрудника</div>
                    </div>
                    <div>
                        <label class="block text-sm font-bold mb-1">Telegram ID <span class="text-gray-400">(не обязательно)</span></label>
                        <input id="staffTelegramId" class="w-full border p-2 rounded" value="${s.telegram_id || ''}" placeholder="Числовой ID">
                        <div class="text-xs text-gray-500 mt-1">Можно добавить позже</div>
                    </div>
                    <div>
                        <label class="block text-sm font-bold mb-1">Должность</label>
                        <select id="staffRole" class="w-full border p-2 rounded">
                            <option value="maid" ${s.role === 'maid' ? 'selected' : ''}>Горничная</option>
                            <option value="technician" ${s.role === 'technician' ? 'selected' : ''}>Тех. специалист</option>
                            <option value="administrator" ${s.role === 'administrator' ? 'selected' : ''}>Администратор</option>
                        </select>
                    </div>
                    <div class="md:col-span-2">
                        <label class="block text-sm font-bold mb-2">Права доступа</label>
                        <div class="flex gap-4 flex-wrap">
                            <label class="flex items-center gap-2">
                                <input type="checkbox" id="permMenu" ${perms.edit_menu ? 'checked' : ''}>
                                <span>Редактировать меню</span>
                            </label>
                            <label class="flex items-center gap-2">
                                <input type="checkbox" id="permGuide" ${perms.edit_guide ? 'checked' : ''}>
                                <span>Редактировать гид</span>
                            </label>
                            <label class="flex items-center gap-2">
                                <input type="checkbox" id="permTickets" ${perms.view_tickets ? 'checked' : ''}>
                                <span>Просмотр заявок</span>
                            </label>
                        </div>
                    </div>
                </div>
                <div class="flex gap-2 mt-4">
                    <button onclick="app.saveStaffWithValidation()" class="bg-green-600 text-white px-6 py-2 rounded-lg font-bold">Сохранить</button>
                    <button onclick="app.editingStaff = null; app.render()" class="border px-6 py-2 rounded-lg">Отмена</button>
                </div>
            </div>
        `;
    }

    saveStaffWithValidation() {
        const name = document.getElementById('staffName').value.trim();
        const phone = document.getElementById('staffPhone').value.trim();
        const telegramId = document.getElementById('staffTelegramId').value.trim();

        if (!name) { alert('Укажите ФИО'); return; }
        if (!phone) { alert('Укажите телефон'); return; }

        this.saveStaff({
            id: this.editingStaff.id || null,
            full_name: name,
            phone: phone,
            telegram_id: telegramId || null,
            role: document.getElementById('staffRole').value,
            permissions: {
                edit_menu: document.getElementById('permMenu').checked,
                edit_guide: document.getElementById('permGuide').checked,
                view_tickets: document.getElementById('permTickets').checked
            },
            is_active: true
        });
    }
    renderStaffTab() {
        return `<div class="space-y-4"><div class="flex justify-between items-center"><h2 class="text-2xl font-bold">🛠 Задачи</h2><button onclick="app.showCreateStaffTask()" class="bg-blue-600 text-white px-4 py-2 rounded-lg font-bold">+</button></div><div class="grid grid-cols-1 md:grid-cols-2 gap-4">${this.staffTasks.map(s => `<div class="bg-white p-4 rounded-xl shadow border-l-4 ${s.status === 'PENDING' ? 'border-red-500' : 'border-green-500'}"><div class="flex items-start justify-between gap-3"><div><div class="font-bold">#${s.room_number}: ${s.task_type}</div><div class="text-xs text-gray-500 mt-1">Ответственный: ${this.getAssignedStaffName(s.assigned_to)}</div><div class="text-xs text-gray-400">${s.status}</div></div>${s.status === 'COMPLETED' ? `<button onclick="app.deleteCompletedTask(${s.id})" class="text-red-500 hover:bg-red-50 rounded-full w-7 h-7 flex items-center justify-center" title="Удалить выполненную задачу">✕</button>` : ''}</div></div>`).join('')}</div>
        <div id="taskModal" class="hidden fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"><div class="bg-white p-8 rounded-2xl w-full max-w-md shadow-2xl"><h3 class="text-xl font-bold mb-4">Новая задача</h3><div class="space-y-4"><input id="taskRoom" class="w-full border p-3 rounded-xl" placeholder="Номер"><select id="taskType" class="w-full border p-3 rounded-xl"><option value="Уборка">Уборка</option><option value="Техническая задача">Техническая задача</option><option value="Доставка">Доставка</option><option value="Прочее">Прочее</option></select><select id="taskAssignee" class="w-full border p-3 rounded-xl">${this.getStaffOptionsHtml()}</select><div class="grid grid-cols-2 gap-2"><select id="taskNotifyMode" class="w-full border p-3 rounded-xl" onchange="app.toggleTaskTimeInput()"><option value="now">Сейчас</option><option value="at_time">Ко времени (МСК)</option></select><input id="taskNotifyTime" type="time" class="w-full border p-3 rounded-xl" style="display:none" placeholder="HH:MM"></div><textarea id="taskDesc" class="w-full border p-3 rounded-xl h-24" placeholder="Описание"></textarea><div class="flex gap-2"><button onclick="app.submitStaffTask()" class="flex-1 bg-blue-600 text-white py-3 rounded-xl font-bold">Создать</button><button onclick="app.hideModal()" class="px-6 border py-3 rounded-xl">Отмена</button></div></div></div></div></div>`;
    }

    renderCamerasTab() {
        // Start auto-refresh when cameras tab is shown
        setTimeout(() => this.startCameraRefresh(), 100);
        return `
            <div class="space-y-6">
                <h2 class="text-2xl font-bold">🎥 Камеры видеонаблюдения</h2>
                <div class="flex gap-4 mb-4">
                    <button onclick="app.refreshCameras()" class="bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center gap-2">
                        <span id="refreshIcon">🔄</span> Обновить
                    </button>
                    <label class="flex items-center gap-2">
                        <input type="checkbox" id="autoRefresh" checked onchange="app.toggleAutoRefresh()">
                        <span class="text-sm">Авто-обновление (20 сек)</span>
                    </label>
                </div>
                
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div class="bg-white p-6 rounded-xl shadow-lg">
                        <h3 class="text-lg font-bold mb-4">📷 Камера 1</h3>
                        <div class="bg-gray-900 rounded-lg overflow-hidden aspect-video flex items-center justify-center relative">
                            <img id="camera1-img" class="w-full h-full object-cover" src="" alt="Камера 1">
                            <div id="camera1-loading" class="absolute inset-0 bg-gray-900 flex items-center justify-center">
                                <span class="text-white">📷 Загрузка...</span>
                            </div>
                        </div>
                        <div class="mt-4 flex gap-2">
                            <button onclick="navigator.clipboard.writeText('rtsp://Sayt:pDA11BkIcwXuKK3@78.36.41.145:8282/0')" class="text-sm bg-blue-100 text-blue-700 px-3 py-1 rounded">📋 Копировать RTSP</button>
                            <a href="vlc://rtsp://Sayt:pDA11BkIcwXuKK3@78.36.41.145:8282/0" class="text-sm bg-orange-100 text-orange-700 px-3 py-1 rounded">▶ VLC</a>
                        </div>
                    </div>
                    
                    <div class="bg-white p-6 rounded-xl shadow-lg">
                        <h3 class="text-lg font-bold mb-4">📷 Камера 2</h3>
                        <div class="bg-gray-900 rounded-lg overflow-hidden aspect-video flex items-center justify-center relative">
                            <img id="camera2-img" class="w-full h-full object-cover" src="" alt="Камера 2">
                            <div id="camera2-loading" class="absolute inset-0 bg-gray-900 flex items-center justify-center">
                                <span class="text-white">📷 Загрузка...</span>
                            </div>
                        </div>
                        <div class="mt-4 flex gap-2">
                            <button onclick="navigator.clipboard.writeText('rtsp://Sayt:pDA11BkIcwXuKK3@78.36.41.145:8282/1')" class="text-sm bg-blue-100 text-blue-700 px-3 py-1 rounded">📋 Копировать RTSP</button>
                            <a href="vlc://rtsp://Sayt:pDA11BkIcwXuKK3@78.36.41.145:8282/1" class="text-sm bg-orange-100 text-orange-700 px-3 py-1 rounded">▶ VLC</a>
                        </div>
                    </div>
                </div>
                
                <div class="bg-green-50 border border-green-200 p-4 rounded-xl">
                    <h4 class="font-bold text-green-800">✅ Просмотр в браузере</h4>
                    <p class="text-sm text-green-700 mt-2">
                        Изображения обновляются каждые 20 секунд. Для полноценного видео используйте VLC.
                    </p>
                </div>
            </div>
        `;
    }

    startCameraRefresh() {
        this.cameraRefreshEnabled = true;
        this.refreshCameras();
        this.cameraRefreshInterval = setInterval(() => {
            if (this.cameraRefreshEnabled && this.currentTab === 'cameras') {
                this.refreshCameras();
            }
        }, 20000);
    }

    stopCameraRefresh() {
        this.cameraRefreshEnabled = false;
        if (this.cameraRefreshInterval) {
            clearInterval(this.cameraRefreshInterval);
            this.cameraRefreshInterval = null;
        }
    }

    toggleAutoRefresh() {
        const checkbox = document.getElementById('autoRefresh');
        if (checkbox.checked) {
            this.startCameraRefresh();
        } else {
            this.stopCameraRefresh();
        }
    }

    refreshCameras() {
        const timestamp = Date.now();
        ['camera1', 'camera2'].forEach(camId => {
            const img = document.getElementById(`${camId}-img`);
            const loading = document.getElementById(`${camId}-loading`);
            if (img) {
                const newImg = new Image();
                newImg.onload = () => {
                    img.src = newImg.src;
                    if (loading) loading.style.display = 'none';
                };
                newImg.onerror = () => {
                    if (loading) {
                        loading.innerHTML = '<span class="text-red-400">❌ Камера недоступна</span>';
                        loading.style.display = 'flex';
                    }
                };
                newImg.src = `${API_BASE}/camera/${camId}/snapshot?t=${timestamp}`;
            }
        });
    }
    showCreateStaffTask() { document.getElementById('taskModal').classList.remove('hidden'); }
    hideModal() { document.getElementById('taskModal').classList.add('hidden'); }
    toggleTaskTimeInput() {
        const mode = document.getElementById('taskNotifyMode')?.value || 'now';
        const timeInput = document.getElementById('taskNotifyTime');
        if (!timeInput) return;
        timeInput.style.display = mode === 'at_time' ? 'block' : 'none';
    }
    async submitStaffTask() {
        const r = document.getElementById('taskRoom').value;
        if (!r) return alert('Укажите номер');
        const assignedTo = document.getElementById('taskAssignee')?.value || null;
        if (!assignedTo) return alert('Выберите ответственного');
        const notifyMode = document.getElementById('taskNotifyMode')?.value || 'now';
        const notifyTimeMsk = document.getElementById('taskNotifyTime')?.value || '';
        if (notifyMode === 'at_time' && !notifyTimeMsk) return alert('Укажите время по МСК');
        await fetch(`${API_BASE}/staff/tasks`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ room_number: r, task_type: document.getElementById('taskType').value, description: document.getElementById('taskDesc').value, assigned_to: assignedTo, notify_mode: notifyMode, notify_time_msk: notifyTimeMsk }) });
        this.hideModal(); this.loadStaffTasks();
    }

    async deleteCompletedTask(taskId) {
        if (!confirm('Удалить выполненную задачу?')) return;
        const resp = await fetch(`${API_BASE}/staff/tasks/${taskId}`, { method: 'DELETE' });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            alert(err.detail || 'Не удалось удалить задачу');
            return;
        }
        await this.loadStaffTasks();
    }

    getAssignedStaffName(assignedTo) {
        if (!assignedTo) return 'Не назначен';
        const assignedStr = String(assignedTo);
        let staff = null;
        if (/^\d+$/.test(assignedStr)) {
            staff = (this.staff || []).find(s => String(s.id) === assignedStr);
        }
        if (!staff) {
            staff = (this.staff || []).find(s => s.telegram_id === assignedStr);
        }
        return staff ? staff.full_name : assignedStr;
    }
    renderMarketingTab() { return `<div class="bg-white p-8 rounded-2xl shadow-xl max-w-xl mx-auto"><h2 class="text-2xl font-bold mb-6">📢 Рассылка</h2><textarea id="broadcastText" class="w-full border p-4 rounded-xl h-40" placeholder="Текст..."></textarea><button onclick="alert('Запущено')" class="w-full bg-green-600 text-white font-bold py-4 rounded-xl mt-4">Отправить всем</button></div>`; }

    getContentScenarios() {
        return [
            {
                section: 'До заезда',
                title: 'Старт и выбор этапа',
                description: 'Гость получает эти тексты сразу после /start и при возврате в выбор этапа.',
                textPaths: [
                    { path: 'greeting.start', label: 'Приветствие' },
                    { path: 'menus.segment_choice_prompt', label: 'Текст выбора этапа' },
                ],
                buttonPaths: [
                    { path: 'segment_menu[0].label', label: 'Кнопка: Я планирую поездку' },
                    { path: 'segment_menu[1].label', label: 'Кнопка: Я уже проживаю в отеле' },
                    { path: 'segment_menu[2].label', label: 'Кнопка: Визуальное меню' },
                ],
            },
            {
                section: 'До заезда',
                title: 'Меню до заезда',
                description: 'Тексты и кнопки, которые видит гость в разделе «Я планирую поездку».',
                textPaths: [
                    { path: 'menus.pre_arrival_title', label: 'Заголовок раздела' },
                    { path: 'pre_arrival.about_hotel', label: 'Сообщение: Об отеле' },
                    { path: 'pre_arrival.how_to_get', label: 'Сообщение: Как добраться' },
                    { path: 'pre_arrival.faq', label: 'Сообщение: Вопросы и ответы' },
                    { path: 'pre_arrival.restaurant', label: 'Сообщение: Ресторан' },
                ],
                buttonPaths: [
                    { path: 'pre_arrival_menu[0].label', label: 'Кнопка: Забронировать номер' },
                    { path: 'pre_arrival_menu[4].label', label: 'Кнопка: Вопросы и ответы' },
                    { path: 'pre_arrival_menu[6].label', label: 'Кнопка: Администратор (до заезда)' },
                ],
            },
            {
                section: 'Во время проживания',
                title: 'Меню проживающего гостя',
                description: 'Основной экран и кнопки для гостя, который уже проживает в отеле.',
                textPaths: [
                    { path: 'menus.in_house_title', label: 'Заголовок раздела' },
                    { path: 'in_house.walks_relax', label: 'Сообщение: Прогулки и отдых' },
                    { path: 'in_house.recommendations', label: 'Сообщение: Рекомендации' },
                    { path: 'in_house.admin', label: 'Сообщение: Администратор' },
                ],
                buttonPaths: [
                    { path: 'in_house_menu[0].label', label: 'Кнопка: Рум-сервис' },
                    { path: 'in_house_menu[1].label', label: 'Кнопка: Завтраки' },
                    { path: 'in_house_menu[3].label', label: 'Кнопка: Погода' },
                    { path: 'in_house_menu[5].label', label: 'Кнопка: Администратор' },
                ],
            },
            {
                section: 'Во время проживания',
                title: 'Рум-сервис',
                description: 'Подсказки и тексты, которые гость получает в ветках рум-сервиса.',
                textPaths: [
                    { path: 'room_service.what_do_you_need', label: 'Текст экрана выбора услуги' },
                    { path: 'room_service.technical_problem.prompt_category', label: 'Тех. проблема: запрос категории' },
                    { path: 'room_service.extra_to_room.prompt_item', label: 'Дополнительно в номер: что принести' },
                    { path: 'room_service.cleaning.prompt_time', label: 'Уборка: выбор времени' },
                    { path: 'room_service.other.prompt_text', label: 'Другое: запрос текста' },
                ],
                buttonPaths: [
                    { path: 'room_service.branches[0].label', label: 'Кнопка: Технические проблемы' },
                    { path: 'room_service.branches[1].label', label: 'Кнопка: Дополнительно в номер' },
                    { path: 'room_service.branches[2].label', label: 'Кнопка: Уборка номера' },
                    { path: 'room_service.branches[3].label', label: 'Кнопка: Меню подушек' },
                    { path: 'room_service.branches[4].label', label: 'Кнопка: Другое' },
                ],
            },
            {
                section: 'Питание',
                title: 'Завтраки и меню',
                description: 'Тексты по завтракам и оформлению заказа.',
                textPaths: [
                    { path: 'breakfast.intro', label: 'Текст: старт завтрака' },
                    { path: 'breakfast.too_late', label: 'Текст: заказ недоступен по времени' },
                    { path: 'breakfast.composition', label: 'Текст: состав завтрака' },
                    { path: 'menu.category_prompt', label: 'Текст: выбор категории меню' },
                    { path: 'menu.order_confirmed', label: 'Текст: подтверждение заказа' },
                ],
                buttonPaths: [
                    { path: 'breakfast.entry_menu[0].label', label: 'Кнопка: Заказать завтрак' },
                    { path: 'breakfast.entry_menu[1].label', label: 'Кнопка: Состав завтрака' },
                    { path: 'breakfast.confirm_menu[0].label', label: 'Кнопка: Подтвердить заказ' },
                    { path: 'breakfast.confirm_menu[1].label', label: 'Кнопка: Отменить' },
                ],
            },
            {
                section: 'Система',
                title: 'Служебные уведомления',
                description: 'Тексты системных и сервисных уведомлений.',
                textPaths: [
                    { path: 'tickets.created_confirmation', label: 'Текст: подтверждение заявки' },
                    { path: 'tickets.resolved', label: 'Текст: заявка решена' },
                    { path: 'tickets.declined', label: 'Текст: заявка отклонена' },
                    { path: 'system.not_authorized', label: 'Текст: нет доступа' },
                    { path: 'system.content_reloaded', label: 'Текст: контент обновлён' },
                ],
                buttonPaths: [],
            },
        ];
    }

    getValueByPath(obj, path) {
        if (!obj || !path) return '';
        const parts = path.split('.');
        let cur = obj;
        for (const p of parts) {
            if (cur == null || typeof cur !== 'object' || !(p in cur)) return '';
            cur = cur[p];
        }
        return typeof cur === 'string' ? cur : '';
    }

    getButtonLabelByPath(path) {
        const item = (this.buttonLabels || []).find((b) => b.path === path);
        return item?.label || '';
    }

    renderScenarioTextField(item) {
        const value = this.getValueByPath(this.textsJson, item.path);
        return `
            <div class="bg-gray-50 border rounded-lg p-3 space-y-2">
                <div class="text-xs font-semibold text-gray-700">${this.escapeHtml(item.label)}</div>
                <div class="text-[10px] text-gray-400 font-mono">${this.escapeHtml(item.path)}</div>
                <textarea
                    class="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500 outline-none h-24"
                    onchange="app.updateTextByPath('${this.escapeHtml(item.path)}', this.value)"
                >${this.escapeHtml(value)}</textarea>
            </div>
        `;
    }

    renderScenarioButtonField(item) {
        const value = this.getButtonLabelByPath(item.path);
        return `
            <div class="bg-blue-50 border border-blue-200 rounded-lg p-3 space-y-2">
                <div class="text-xs font-semibold text-blue-900">${this.escapeHtml(item.label)}</div>
                <div class="text-[10px] text-blue-400 font-mono">${this.escapeHtml(item.path)}</div>
                <input
                    class="button-label-input w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none bg-white"
                    data-path="${this.escapeHtml(item.path)}"
                    value="${this.escapeHtml(value)}"
                    placeholder="Название кнопки..."
                />
            </div>
        `;
    }

    renderContentEditorTab() {
        const scenarios = this.getContentScenarios();
        const groupedScenarios = {};
        scenarios.forEach((s) => {
            if (!groupedScenarios[s.section]) groupedScenarios[s.section] = [];
            groupedScenarios[s.section].push(s);
        });

        return `
            <div class="space-y-8">
                <div class="flex justify-between items-center">
                    <h2 class="text-2xl font-bold">📝 Контент по сценарию гостя</h2>
                    <div class="flex gap-2">
                        <button onclick="Promise.all([app.loadMenusYaml(), app.loadMenusJson(), app.loadTextsYaml(), app.loadTextsJson(), app.loadButtonLabels()]).then(() => app.render())" class="bg-blue-600 text-white px-4 py-2 rounded-lg font-bold">🔄 Обновить всё</button>
                    </div>
                </div>

                <div class="bg-green-50 border border-green-200 p-4 rounded-xl text-sm text-green-900">
                    Здесь всё разбито по реальным сценариям гостя: <b>когда</b> бот отправляет сообщение и <b>какие кнопки</b> в этот момент видит гость.
                    Вы редактируете только тексты и подписи кнопок, логика бота не меняется.
                </div>

                ${Object.entries(groupedScenarios).map(([section, sectionScenarios]) => `
                    <section class="space-y-4">
                        <div class="flex items-center gap-2 border-b-2 border-gray-300 pb-2">
                            <h3 class="text-xl font-bold">${this.escapeHtml(section)}</h3>
                        </div>
                        <div class="space-y-4">
                            ${sectionScenarios.map((scenario) => `
                                <div class="bg-white p-4 rounded-xl shadow border">
                                    <div class="mb-3">
                                        <h4 class="font-bold text-lg">${this.escapeHtml(scenario.title)}</h4>
                                        <div class="text-sm text-gray-600">${this.escapeHtml(scenario.description)}</div>
                                    </div>
                                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                        <div class="space-y-3">
                                            <div class="text-xs uppercase tracking-wider text-green-700 font-bold">Сообщения бота</div>
                                            ${scenario.textPaths.map((item) => this.renderScenarioTextField(item)).join('')}
                                        </div>
                                        <div class="space-y-3">
                                            <div class="text-xs uppercase tracking-wider text-blue-700 font-bold">Кнопки на экране</div>
                                            ${scenario.buttonPaths.length
                                                ? scenario.buttonPaths.map((item) => this.renderScenarioButtonField(item)).join('')
                                                : '<div class="text-sm text-gray-400">В этом сценарии кнопки не редактируются</div>'}
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </section>
                `).join('')}

                <div class="flex justify-end">
                    <button onclick="app.saveButtonLabels()" class="bg-green-600 text-white px-6 py-3 rounded-xl font-bold shadow-lg hover:bg-green-700 transition">Сохранить все названия кнопок</button>
                </div>
                ${this.buttonLabelsStatus ? `<div class="text-center text-sm font-bold text-green-600">${this.escapeHtml(this.buttonLabelsStatus)}</div>` : ''}

                <!-- Расширенный редактор (YAML) -->
                <section class="space-y-4 pt-8 border-t">
                    <h3 class="text-lg font-bold text-gray-500">🛠 Расширенный редактор (YAML)</h3>
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <div class="bg-white p-4 rounded-xl shadow border">
                            <label class="block text-sm font-bold mb-2 text-blue-800">menus.ru.yml (Структура меню)</label>
                            <textarea id="menusYamlEditor" class="w-full border rounded-lg p-3 font-mono text-[10px] h-[400px] leading-tight focus:ring-2 focus:ring-blue-500 outline-none bg-gray-50">${this.escapeHtml(this.menusYamlContent || '')}</textarea>
                            <div class="flex gap-2 mt-3">
                                <button onclick="app.saveMenusYaml()" class="bg-blue-600 text-white px-4 py-2 rounded-lg font-bold text-sm">Сохранить структуру</button>
                            </div>
                            ${this.menusYamlStatus ? `<div class="mt-2 text-xs font-bold text-blue-600">${this.escapeHtml(this.menusYamlStatus)}</div>` : ''}
                        </div>
                        <div class="bg-white p-4 rounded-xl shadow border">
                            <label class="block text-sm font-bold mb-2 text-green-800">texts.ru.yml (Все тексты)</label>
                            <textarea id="textsYamlEditor" class="w-full border rounded-lg p-3 font-mono text-[10px] h-[400px] leading-tight focus:ring-2 focus:ring-green-500 outline-none bg-gray-50">${this.escapeHtml(this.textsYamlContent || '')}</textarea>
                            <div class="flex gap-2 mt-3">
                                <button onclick="app.saveTextsYaml()" class="bg-green-600 text-white px-4 py-2 rounded-lg font-bold text-sm">Сохранить тексты</button>
                            </div>
                            ${this.textsYamlStatus ? `<div class="mt-2 text-xs font-bold text-green-600">${this.escapeHtml(this.textsYamlStatus)}</div>` : ''}
                        </div>
                    </div>
                </section>
            </div>
        `;
    }

    async updateTextByPath(path, newValue) {
        try {
            const resp = await fetch(`${API_BASE}/content/texts-ru/json`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path, value: newValue }),
            });
            if (resp.ok) {
                this.textsYamlStatus = 'Текст сохранён';
                await this.loadTextsYaml();
                await this.loadTextsJson();
                this.render();
            }
        } catch (e) {
            console.error(e);
        }
    }

    renderGuestLayout() {
        return `
            <div class="min-h-screen bg-white pb-24">
                <header class="bg-green-800 text-white p-8 rounded-b-[40px] shadow-xl text-center">
                    <h1 class="text-3xl font-black tracking-tight">🏨 Отель GORA</h1>
                    <p class="text-sm opacity-80 mt-1">Добро пожаловать в Сортавала!</p>
                </header>
                <div class="container mx-auto px-6 mt-8">${this.renderGuestTab()}</div>
                <nav class="fixed bottom-6 left-6 right-6 bg-white/80 backdrop-blur-xl border border-gray-100 shadow-2xl rounded-3xl flex justify-around p-4 z-50">
                    <button onclick="app.switchTab('guest_home')" class="flex flex-col items-center ${this.currentTab === 'guest_home' ? 'text-green-700 scale-110' : 'text-gray-400'} transition-all"><span class="text-2xl">🏠</span><span class="text-[10px] font-bold mt-1">Главная</span></button>
                    <button onclick="app.switchTab('guest_booking')" class="flex flex-col items-center ${this.currentTab === 'guest_booking' ? 'text-green-700 scale-110' : 'text-gray-400'} transition-all"><span class="text-2xl">🛏</span><span class="text-[10px] font-bold mt-1">Бронь</span></button>
                    <button onclick="app.switchTab('guest_menu')" class="flex flex-col items-center ${this.currentTab === 'guest_menu' ? 'text-green-700 scale-110' : 'text-gray-400'} transition-all"><span class="text-2xl">🍴</span><span class="text-[10px] font-bold mt-1">Меню</span></button>
                    <button onclick="app.switchTab('guest_guide')" class="flex flex-col items-center ${this.currentTab === 'guest_guide' ? 'text-green-700 scale-110' : 'text-gray-400'} transition-all"><span class="text-2xl">🗺</span><span class="text-[10px] font-bold mt-1">Гид</span></button>
                </nav>
            </div>
        `;
    }

    renderGuestTab() {
        switch (this.currentTab) {
            case 'guest_home': return `
                <div class="space-y-6">
                    <div class="bg-green-50 p-8 rounded-[32px] border border-green-100 text-center">
                        <div class="text-4xl mb-4">📡</div>
                        <h2 class="font-black text-green-900 text-xl mb-2">Бесплатный Wi-Fi</h2>
                        <p class="text-sm text-green-700 mb-6">Сеть: <b>GORA_GUEST</b><br>Пароль: <code>gora2024</code></p>
                        <button onclick="window.Telegram.WebApp.openTelegramLink('https://t.me/Gora_Hotel_Bot')" class="w-full bg-green-600 text-white py-4 rounded-2xl font-black shadow-lg">Написать администратору</button>
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                        <div class="bg-gray-50 p-6 rounded-[28px] text-center shadow-sm border border-gray-100"><span class="text-3xl block mb-2">🍳</span><b class="text-sm">Завтраки</b><p class="text-[10px] text-gray-400 mt-1">08:00 - 10:00</p></div>
                        <div class="bg-gray-50 p-6 rounded-[28px] text-center shadow-sm border border-gray-100"><span class="text-3xl block mb-2">🛎</span><b class="text-sm">Рум-сервис</b><p class="text-[10px] text-gray-400 mt-1">Круглосуточно</p></div>
                    </div>
                    <div class="bg-blue-50 p-6 rounded-[28px] text-center shadow-sm border border-blue-100">
                        <span class="text-3xl block mb-2">📸</span>
                        <b class="text-sm">Регистрация</b>
                        <p class="text-[10px] text-blue-600 mt-1">Пришлите фото паспорта в чат</p>
                    </div>
                </div>`;
            case 'guest_menu': return `<div class="space-y-4"><h2 class="text-2xl font-black mb-6">🍴 Меню</h2>${this.menu.map(m => `<div class="bg-white p-4 rounded-2xl shadow-sm border flex justify-between items-center"><div><div class="font-bold">${m.name}</div><div class="text-green-700 font-black mt-1">${m.price} ₽</div></div><button onclick="window.Telegram.WebApp.sendData('order_${m.id}')" class="bg-green-600 text-white px-4 py-2 rounded-xl text-xs font-bold shadow-md">Заказать</button></div>`).join('')}</div>`;
            case 'guest_guide': return `<div class="space-y-4"><h2 class="text-2xl font-black mb-6">🗺 Гид</h2>${this.guide.map(g => `<div class="bg-white p-5 rounded-2xl border border-gray-100 shadow-sm"><div class="font-bold text-lg">${g.name}</div><p class="text-xs text-gray-500 mt-2 mb-4">${g.description}</p><a href="${g.map_url}" target="_blank" class="text-blue-600 font-bold text-xs flex items-center gap-1">📍 Открыть в картах</a></div>`).join('')}</div>`;
            case 'guest_booking': return `<div class="space-y-4"><h2 class="text-2xl font-black mb-6">🛏 Бронирование</h2><div class="bg-blue-50 p-8 rounded-[32px] text-center border border-blue-100"><p class="text-sm text-blue-800 mb-6">Выберите даты и забронируйте номер</p><button onclick="app.switchTab('shelter')" class="w-full bg-blue-600 text-white py-4 rounded-2xl font-black shadow-xl">Выбрать номер</button></div></div>`;
            case 'shelter': return this.renderShelterTab();
            default: return '<div class="text-center py-20">Загрузка...</div>';
        }
    }
}

window.app = new AdminApp();
