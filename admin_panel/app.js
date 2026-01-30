const API_BASE = '/api';

class AdminApp {
    constructor() {
        this.tickets = [];
        this.currentTicket = null;
        this.stats = null;
        this.hotelParams = null;
        this.availability = null;
        this.menu = [];
        this.guide = [];
        this.staffTasks = [];
        this.users = [];
        this.currentTab = 'tickets';
        this.isUserAdmin = false;
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
                this.loadGuide(),
                this.loadStaffTasks(),
                this.loadUsers()
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
            if (this.isUserAdmin && this.currentTab === 'tickets') {
                this.loadStatistics();
                this.loadTickets();
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

    async loadTickets(status = null) {
        try {
            const url = status ? `${API_BASE}/tickets?status=${status}` : `${API_BASE}/tickets`;
            const response = await fetch(url);
            this.tickets = await response.json();
            this.renderTicketList();
        } catch (e) { console.error(e); }
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

    async loadGuide() {
        try {
            const r = await fetch(`${API_BASE}/guide`);
            this.guide = await r.json();
        } catch (e) { console.error(e); }
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
                            <button onclick="app.switchTab('staff')" class="px-4 py-2 rounded-lg ${this.currentTab === 'staff' ? 'bg-green-700 shadow-inner font-bold' : 'hover:bg-green-700'}">Персонал</button>
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
                                    <button onclick="app.loadTickets()" class="px-4 py-2 bg-blue-600 text-white rounded-lg">Все</button>
                                    <button onclick="app.loadTickets('PENDING_ADMIN')" class="px-4 py-2 bg-orange-600 text-white rounded-lg">Ожидают</button>
                                    <button onclick="app.loadTickets('COMPLETED')" class="px-4 py-2 bg-green-600 text-white rounded-lg">Решено</button>
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
        switch(this.currentTab) {
            case 'shelter': return this.renderShelterTab();
            case 'menu': return this.renderMenuTab();
            case 'guide': return this.renderGuideTab();
            case 'staff': return this.renderStaffTab();
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

    renderTicketList() {
        const container = document.getElementById('ticketList');
        if (!container) return;
        const colors = { 'NEW': 'bg-blue-100 text-blue-800', 'PENDING_ADMIN': 'bg-orange-100 text-orange-800', 'COMPLETED': 'bg-green-100 text-green-800', 'DECLINED': 'bg-red-100 text-red-800' };
        container.innerHTML = this.tickets.map(t => `
            <div onclick="app.loadTicketDetail(${t.id})" class="bg-white p-4 rounded-xl shadow hover:shadow-md cursor-pointer border-l-4 ${t.status === 'PENDING_ADMIN' ? 'border-orange-500' : 'border-gray-200'} transition">
                <div class="flex justify-between items-start">
                    <div class="font-bold text-lg">Заявка #${t.id}</div>
                    <span class="text-[10px] px-2 py-1 rounded-full font-bold ${colors[t.status] || 'bg-gray-100'}">${t.status}</span>
                </div>
                <div class="text-sm text-gray-600 mt-2">
                    <div>👤 ${t.guest_name || t.guest_chat_id}</div>
                    <div class="text-[10px] text-gray-400 mt-1">🕐 ${new Date(t.created_at).toLocaleString('ru-RU')}</div>
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
            <div class="p-3 rounded-2xl ${m.sender === 'ADMIN' ? 'bg-blue-50 ml-8' : 'bg-gray-100 mr-8'} mb-3">
                <div class="flex items-center gap-2 mb-1 text-[10px] font-bold text-gray-500">
                    <span>${m.sender === 'ADMIN' ? '👨‍💼 ' + (m.admin_name || 'Админ') : '👤 Гость'}</span>
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
                <div class="max-h-[400px] overflow-y-auto mb-6 px-2">${msgs}</div>
                ${(t.status === 'NEW' || t.status === 'PENDING_ADMIN') ? `
                    <div class="space-y-3">
                        <textarea id="messageInput" class="w-full border-2 border-gray-100 rounded-2xl p-4 text-sm focus:border-blue-500 outline-none transition h-32" placeholder="Напишите ответ гостю..."></textarea>
                        <div class="flex gap-2">
                            <button onclick="app.handleSendMessage()" class="flex-1 bg-blue-600 text-white font-bold py-3 rounded-xl hover:bg-blue-700 transition">Отправить</button>
                            <button onclick="app.updateTicketStatus(${t.id}, 'COMPLETED')" class="bg-green-600 text-white font-bold px-6 rounded-xl hover:bg-green-700 transition">✅ Выполнено</button>
                            <button onclick="app.updateTicketStatus(${t.id}, 'DECLINED')" class="bg-red-500 text-white font-bold px-6 rounded-xl hover:bg-red-600 transition">❌ Отклонить</button>
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
        if (r.ok) await this.loadTicketDetail(ticketId);
    }

    async updateTicketStatus(id, status) {
        const r = await fetch(`${API_BASE}/tickets/${id}/status`, {
            method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status })
        });
        if (r.ok) { await this.loadTicketDetail(id); await this.loadTickets(); await this.loadStatistics(); }
    }

    handleSendMessage() {
        const input = document.getElementById('messageInput');
        if (input?.value.trim() && this.currentTicket) {
            this.sendMessage(this.currentTicket.id, input.value.trim());
            input.value = '';
        }
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
                                <div class="flex justify-between border-b pb-2"><span>Город:</span> <span class="font-semibold">${h.hotel_info.hotelCity || 'Теберда'}</span></div>
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
                        <input type="date" id="checkOut" class="border rounded-lg p-2" value="${new Date(Date.now()+86400000).toISOString().split('T')[0]}">
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

    renderMenuTab() { return `<div class="space-y-4"><div class="flex justify-between items-center"><h2 class="text-2xl font-bold">🍴 Меню</h2><button class="bg-green-600 text-white px-4 py-2 rounded-lg font-bold">+</button></div><div class="grid grid-cols-1 md:grid-cols-3 gap-4">${this.menu.map(m => `<div class="bg-white p-4 rounded-xl shadow flex justify-between"><div><div class="font-bold">${m.name}</div><div class="text-xs text-gray-400">${m.price} ₽</div></div><button class="text-red-400">🗑</button></div>`).join('')}</div></div>`; }
    renderGuideTab() { return `<div class="space-y-4"><div class="flex justify-between items-center"><h2 class="text-2xl font-bold">🗺 Гид</h2><button class="bg-green-600 text-white px-4 py-2 rounded-lg font-bold">+</button></div><div class="grid grid-cols-1 md:grid-cols-3 gap-4">${this.guide.map(g => `<div class="bg-white p-4 rounded-xl shadow"><div class="font-bold">${g.name}</div><div class="text-xs text-gray-500 mt-1">${g.description}</div></div>`).join('')}</div></div>`; }
    renderStaffTab() {
        return `<div class="space-y-4"><div class="flex justify-between items-center"><h2 class="text-2xl font-bold">🛠 Задачи</h2><button onclick="app.showCreateStaffTask()" class="bg-blue-600 text-white px-4 py-2 rounded-lg font-bold">+</button></div><div class="grid grid-cols-1 md:grid-cols-2 gap-4">${this.staffTasks.map(s => `<div class="bg-white p-4 rounded-xl shadow border-l-4 ${s.status === 'PENDING' ? 'border-red-500' : 'border-green-500'}"><div class="font-bold">#${s.room_number}: ${s.task_type}</div><div class="text-xs text-gray-400">${s.status}</div></div>`).join('')}</div>
        <div id="taskModal" class="hidden fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"><div class="bg-white p-8 rounded-2xl w-full max-w-md shadow-2xl"><h3 class="text-xl font-bold mb-4">Новая задача</h3><div class="space-y-4"><input id="taskRoom" class="w-full border p-3 rounded-xl" placeholder="Номер"><select id="taskType" class="w-full border p-3 rounded-xl"><option value="Уборка">Уборка</option></select><textarea id="taskDesc" class="w-full border p-3 rounded-xl h-24" placeholder="Описание"></textarea><div class="flex gap-2"><button onclick="app.submitStaffTask()" class="flex-1 bg-blue-600 text-white py-3 rounded-xl font-bold">Создать</button><button onclick="app.hideModal()" class="px-6 border py-3 rounded-xl">Отмена</button></div></div></div></div></div>`;
    }
    showCreateStaffTask() { document.getElementById('taskModal').classList.remove('hidden'); }
    hideModal() { document.getElementById('taskModal').classList.add('hidden'); }
    async submitStaffTask() {
        const r = document.getElementById('taskRoom').value;
        if (!r) return alert('Укажите номер');
        await fetch(`${API_BASE}/staff/tasks`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ room_number: r, task_type: document.getElementById('taskType').value, description: document.getElementById('taskDesc').value }) });
        this.hideModal(); this.loadStaffTasks();
    }
    renderMarketingTab() { return `<div class="bg-white p-8 rounded-2xl shadow-xl max-w-xl mx-auto"><h2 class="text-2xl font-bold mb-6">📢 Рассылка</h2><textarea id="broadcastText" class="w-full border p-4 rounded-xl h-40" placeholder="Текст..."></textarea><button onclick="alert('Запущено')" class="w-full bg-green-600 text-white font-bold py-4 rounded-xl mt-4">Отправить всем</button></div>`; }

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
        switch(this.currentTab) {
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
