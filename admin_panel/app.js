const API_BASE = 'http://localhost:8000/api';

class AdminApp {
    constructor() {
        this.tickets = [];
        this.currentTicket = null;
        this.stats = null;
        this.init();
    }

    async init() {
        await this.loadStatistics();
        await this.loadTickets();
        this.render();
        // Auto-refresh every 10 seconds
        setInterval(() => {
            this.loadStatistics();
            this.loadTickets();
        }, 10000);
    }

    async loadStatistics() {
        try {
            const response = await fetch(`${API_BASE}/statistics`);
            this.stats = await response.json();
            this.renderStatistics();
        } catch (error) {
            console.error('Failed to load statistics:', error);
        }
    }

    async loadTickets(status = null) {
        try {
            const url = status ? `${API_BASE}/tickets?status=${status}` : `${API_BASE}/tickets`;
            const response = await fetch(url);
            this.tickets = await response.json();
            this.renderTicketList();
        } catch (error) {
            console.error('Failed to load tickets:', error);
        }
    }

    async loadTicketDetail(ticketId) {
        try {
            const response = await fetch(`${API_BASE}/tickets/${ticketId}`);
            this.currentTicket = await response.json();
            this.renderTicketDetail();
        } catch (error) {
            console.error('Failed to load ticket:', error);
        }
    }

    async sendMessage(ticketId, content) {
        try {
            // Get Telegram WebApp user data if available
            let adminTelegramId = null;
            let adminName = null;
            
            if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initDataUnsafe) {
                const user = window.Telegram.WebApp.initDataUnsafe.user;
                if (user) {
                    adminTelegramId = user.id.toString();
                    adminName = user.first_name + (user.last_name ? ' ' + user.last_name : '');
                }
            }
            
            const response = await fetch(`${API_BASE}/tickets/${ticketId}/messages`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    content,
                    admin_telegram_id: adminTelegramId,
                    admin_name: adminName
                })
            });
            if (response.ok) {
                await this.loadTicketDetail(ticketId);
            }
        } catch (error) {
            console.error('Failed to send message:', error);
        }
    }

    async updateTicketStatus(ticketId, status) {
        try {
            const response = await fetch(`${API_BASE}/tickets/${ticketId}/status`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status })
            });
            if (response.ok) {
                await this.loadTicketDetail(ticketId);
                await this.loadTickets();
                await this.loadStatistics();
            }
        } catch (error) {
            console.error('Failed to update status:', error);
        }
    }

    renderStatistics() {
        if (!this.stats) return;
        
        const statsHTML = `
            <div class="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
                <div class="bg-white p-4 rounded-lg shadow">
                    <div class="text-sm text-gray-600">Заявок сегодня</div>
                    <div class="text-2xl font-bold text-blue-600">${this.stats.total_tickets_today}</div>
                </div>
                <div class="bg-white p-4 rounded-lg shadow">
                    <div class="text-sm text-gray-600">Ожидают</div>
                    <div class="text-2xl font-bold text-orange-600">${this.stats.pending_tickets}</div>
                </div>
                <div class="bg-white p-4 rounded-lg shadow">
                    <div class="text-sm text-gray-600">Решено сегодня</div>
                    <div class="text-2xl font-bold text-green-600">${this.stats.completed_today}</div>
                </div>
                <div class="bg-white p-4 rounded-lg shadow">
                    <div class="text-sm text-gray-600">Отклонено сегодня</div>
                    <div class="text-2xl font-bold text-red-600">${this.stats.declined_today}</div>
                </div>
                <div class="bg-white p-4 rounded-lg shadow">
                    <div class="text-sm text-gray-600">Всего активных</div>
                    <div class="text-2xl font-bold text-purple-600">${this.stats.total_active}</div>
                </div>
            </div>
        `;
        
        document.getElementById('statistics').innerHTML = statsHTML;
    }

    renderTicketList() {
        const ticketListHTML = this.tickets.map(ticket => {
            const statusColors = {
                'NEW': 'bg-blue-100 text-blue-800',
                'PENDING_ADMIN': 'bg-orange-100 text-orange-800',
                'COMPLETED': 'bg-green-100 text-green-800',
                'DECLINED': 'bg-red-100 text-red-800',
                'CANCELLED': 'bg-gray-100 text-gray-800'
            };
            
            const typeNames = {
                'ROOM_SERVICE': 'Рум-сервис',
                'BREAKFAST': 'Завтрак',
                'PRE_ARRIVAL': 'До заезда',
                'OTHER': 'Другое'
            };
            
            const statusColor = statusColors[ticket.status] || 'bg-gray-100';
            const typeName = typeNames[ticket.type] || ticket.type;
            const guestName = ticket.guest_name || `ID: ${ticket.guest_chat_id}`;
            const roomNumber = ticket.room_number ? `Номер: ${ticket.room_number}` : '';
            
            return `
                <div class="bg-white p-4 rounded-lg shadow hover:shadow-md transition cursor-pointer border-l-4 ${ticket.status === 'PENDING_ADMIN' ? 'border-orange-500' : 'border-gray-300'}"
                     onclick="app.loadTicketDetail(${ticket.id})">
                    <div class="flex justify-between items-start mb-2">
                        <div class="font-bold text-lg">Заявка #${ticket.id}</div>
                        <span class="px-2 py-1 rounded text-xs ${statusColor}">${ticket.status}</span>
                    </div>
                    <div class="text-sm text-gray-600 space-y-1">
                        <div>📝 ${typeName}</div>
                        <div>👤 ${guestName}</div>
                        ${roomNumber ? `<div>🚪 ${roomNumber}</div>` : ''}
                        <div>🕐 ${new Date(ticket.created_at).toLocaleString('ru-RU')}</div>
                    </div>
                </div>
            `;
        }).join('');
        
        document.getElementById('ticketList').innerHTML = ticketListHTML || '<div class="text-center text-gray-500 py-8">Нет заявок</div>';
    }

    renderTicketDetail() {
        if (!this.currentTicket) {
            document.getElementById('ticketDetail').innerHTML = '<div class="text-center text-gray-500 py-8">Выберите заявку</div>';
            return;
        }
        
        const ticket = this.currentTicket;
        const typeNames = {
            'ROOM_SERVICE': 'Рум-сервис',
            'BREAKFAST': 'Завтрак',
            'PRE_ARRIVAL': 'До заезда',
            'OTHER': 'Другое'
        };
        
        const messagesHTML = ticket.messages.map(msg => {
            const isAdmin = msg.sender === 'ADMIN';
            const icon = isAdmin ? '👨‍💼' : '👤';
            const bgColor = isAdmin ? 'bg-blue-50' : 'bg-gray-50';
            const senderName = isAdmin && msg.admin_name ? msg.admin_name : msg.sender;
            
            return `
                <div class="${bgColor} p-3 rounded-lg mb-2">
                    <div class="flex items-center gap-2 mb-1">
                        <span>${icon}</span>
                        <span class="text-sm font-medium">${senderName}</span>
                        <span class="text-xs text-gray-500">${new Date(msg.created_at).toLocaleString('ru-RU')}</span>
                    </div>
                    <div class="text-sm">${this.escapeHtml(msg.content)}</div>
                </div>
            `;
        }).join('');
        
        const canRespond = ticket.status === 'NEW' || ticket.status === 'PENDING_ADMIN';
        
        const detailHTML = `
            <div class="bg-white p-6 rounded-lg shadow">
                <div class="flex justify-between items-start mb-4">
                    <h2 class="text-2xl font-bold">Заявка #${ticket.id}</h2>
                    <button onclick="app.currentTicket = null; app.render()" class="text-gray-500 hover:text-gray-700">✕</button>
                </div>
                
                <div class="grid grid-cols-2 gap-4 mb-6 text-sm">
                    <div><span class="font-semibold">Тип:</span> ${typeNames[ticket.type] || ticket.type}</div>
                    <div><span class="font-semibold">Статус:</span> ${ticket.status}</div>
                    <div><span class="font-semibold">Гость:</span> ${ticket.guest_name || ticket.guest_chat_id}</div>
                    ${ticket.room_number ? `<div><span class="font-semibold">Номер:</span> ${ticket.room_number}</div>` : ''}
                    <div><span class="font-semibold">Создана:</span> ${new Date(ticket.created_at).toLocaleString('ru-RU')}</div>
                    <div><span class="font-semibold">Обновлена:</span> ${new Date(ticket.updated_at).toLocaleString('ru-RU')}</div>
                </div>
                
                <div class="mb-6">
                    <h3 class="font-bold mb-3">История сообщений:</h3>
                    <div class="space-y-2 max-h-96 overflow-y-auto">
                        ${messagesHTML}
                    </div>
                </div>
                
                ${canRespond ? `
                    <div class="mb-4">
                        <label class="block font-semibold mb-2">Ответить гостю:</label>
                        <textarea id="messageInput" class="w-full border rounded-lg p-3 h-24" placeholder="Введите ваш ответ..."></textarea>
                        <button onclick="app.handleSendMessage()" class="mt-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
                            Отправить
                        </button>
                    </div>
                ` : ''}
                
                <div class="flex gap-2">
                    ${ticket.status !== 'COMPLETED' ? `
                        <button onclick="app.updateTicketStatus(${ticket.id}, 'COMPLETED')" 
                                class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700">
                            ✅ Решено
                        </button>
                    ` : ''}
                    ${ticket.status !== 'DECLINED' ? `
                        <button onclick="app.updateTicketStatus(${ticket.id}, 'DECLINED')" 
                                class="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700">
                            ❌ Отклонить
                        </button>
                    ` : ''}
                </div>
            </div>
        `;
        
        document.getElementById('ticketDetail').innerHTML = detailHTML;
    }

    handleSendMessage() {
        const input = document.getElementById('messageInput');
        const content = input.value.trim();
        
        if (content && this.currentTicket) {
            this.sendMessage(this.currentTicket.id, content);
            input.value = '';
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    render() {
        const appHTML = `
            <div class="min-h-screen bg-gray-50">
                <header class="bg-green-800 text-white p-6 shadow-lg">
                    <h1 class="text-3xl font-bold">🏨 GORA Hotel - Админ Панель</h1>
                    <p class="text-sm opacity-90">Управление заявками гостей</p>
                </header>
                
                <div class="container mx-auto p-6">
                    <div id="statistics"></div>
                    
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <div>
                            <div class="mb-4 flex gap-2">
                                <button onclick="app.loadTickets()" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">Все</button>
                                <button onclick="app.loadTickets('PENDING_ADMIN')" class="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700">Ожидают</button>
                                <button onclick="app.loadTickets('COMPLETED')" class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">Решено</button>
                            </div>
                            <div id="ticketList" class="space-y-4 max-h-screen overflow-y-auto"></div>
                        </div>
                        
                        <div id="ticketDetail"></div>
                    </div>
                </div>
            </div>
        `;
        
        document.getElementById('app').innerHTML = appHTML;
        this.renderStatistics();
        this.renderTicketList();
        this.renderTicketDetail();
    }
}

// Initialize app
const app = new AdminApp();
