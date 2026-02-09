import React, { useState, useEffect } from 'react';

// Mock Telegram WebApp SDK for local development
const WebApp = (window as any).Telegram?.WebApp || {
  ready: () => { },
  expand: () => { },
  sendData: (data: string) => console.log('SendData:', data),
  close: () => { },
};

type MenuKey = 'main' | 'planning' | 'staying' | 'visual';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('home');
  // Какое меню показываем на стартовом экране
  const [currentMenu, setCurrentMenu] = useState<MenuKey>('main');

  useEffect(() => {
    WebApp.ready();
    WebApp.expand();
  }, []);

  const sendMenuMessage = (text: string) => {
    WebApp.sendData(JSON.stringify({ action: 'suggested_question', text }));
  };

  const handleServiceClick = (service: string) => {
    WebApp.sendData(JSON.stringify({ action: 'book_service', service }));
    WebApp.close();
  };

  // Вложенное меню на стартовом экране (главное + подменю "Визуальное меню")
  if (activeTab === 'home') {
    return (
      <div className="min-h-screen bg-sand font-sans flex flex-col justify-center items-center p-6 animate-fade-in relative overflow-hidden">
        {/* Background blobs */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-400/10 rounded-full -mr-20 -mt-20 blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-emerald-600/10 rounded-full -ml-10 -mb-10 blur-2xl pointer-events-none" />

        <div className="text-center mb-10 z-10">
          <h1 className="text-3xl font-extrabold text-emerald-900 mb-2 tracking-tight">Отель «ГОРА»</h1>
          <p className="text-slate-600 font-medium">
            {currentMenu === 'main' && 'Чем мы можем вам помочь?'}
            {currentMenu === 'planning' && 'Я планирую поездку'}
            {currentMenu === 'staying' && 'Я уже проживаю в отеле'}
            {currentMenu === 'visual' && 'Визуальное меню'}
          </p>
        </div>

        <div className="w-full max-w-sm space-y-4 z-10">
          {currentMenu === 'main' && (
            <>
              <button
                onClick={() => setCurrentMenu('planning')}
                className="w-full glass-card p-5 text-left font-bold text-slate-800 hover:bg-white/60 active:scale-[0.98] transition-all shadow-md hover:shadow-lg flex items-center group"
              >
                <span className="text-2xl mr-4 group-hover:scale-110 transition-transform duration-300">✈️</span>
                <span>Я планирую поездку</span>
              </button>

              <button
                onClick={() => setCurrentMenu('staying')}
                className="w-full glass-card p-5 text-left font-bold text-slate-800 hover:bg-white/60 active:scale-[0.98] transition-all shadow-md hover:shadow-lg flex items-center group"
              >
                <span className="text-2xl mr-4 group-hover:scale-110 transition-transform duration-300">🏨</span>
                <span>Я уже проживаю в отеле</span>
              </button>

              <button
                onClick={() => setCurrentMenu('visual')}
                className="w-full glass-card p-5 text-left font-bold text-slate-800 hover:bg-white/60 active:scale-[0.98] transition-all shadow-md hover:shadow-lg flex items-center group"
              >
                <span className="text-2xl mr-4 group-hover:scale-110 transition-transform duration-300">🗓️</span>
                <span>Визуальное меню 🗓️</span>
              </button>
            </>
          )}

          {currentMenu === 'planning' && (
            <>
              {[
                '🏨 Забронировать номер',
                '🛏️ Номера и цены',
                '🌲 Об отеле',
                '🎉 Мероприятия и банкеты',
                '📍 Как добраться',
                '❓ Вопросы и ответы',
                '🍽️ Ресторан',
                '📞 Связаться с администратором',
              ].map((label) => (
                <button
                  key={label}
                  onClick={() => sendMenuMessage(label)}
                  className="w-full glass-card p-4 text-left font-semibold text-slate-800 hover:bg-white/60 active:scale-[0.98] transition-all shadow-md hover:shadow-lg flex items-center"
                >
                  <span>{label}</span>
                </button>
              ))}

              <button
                onClick={() => setCurrentMenu('main')}
                className="w-full glass-card p-4 text-center font-bold text-slate-700 hover:bg-white/70 active:scale-[0.98] transition-all shadow-md hover:shadow-lg"
              >
                🔙 Назад
              </button>
            </>
          )}

          {currentMenu === 'staying' && (
            <>
              {[
                '🍳 Завтраки',
                '🗺 Гид по Сортавала',
                '🌤 Погода и Камеры',
                '🆘 SOS / Помощь',
                '👤 Личный кабинет',
                '📞 Администратор',
              ].map((label) => (
                <button
                  key={label}
                  onClick={() => sendMenuMessage(label)}
                  className="w-full glass-card p-4 text-left font-semibold text-slate-800 hover:bg-white/60 active:scale-[0.98] transition-all shadow-md hover:shadow-lg flex items-center"
                >
                  <span>{label}</span>
                </button>
              ))}

              <button
                onClick={() => setCurrentMenu('main')}
                className="w-full glass-card p-4 text-center font-bold text-slate-700 hover:bg-white/70 active:scale-[0.98] transition-all shadow-md hover:shadow-lg"
              >
                🔙 Назад
              </button>
            </>
          )}

          {currentMenu === 'visual' && (
            <>
              {[
                '🏨 Забронировать номер',
                '🛏️ Номера и цены',
                '🌲 Об отеле',
                '🎉 Мероприятия и банкеты',
                '📍 Как добраться',
                '❓ Вопросы и ответы',
                '🍽️ Ресторан',
                '📞 Связаться с администратором',
              ].map((label) => (
                <button
                  key={label}
                  onClick={() => sendMenuMessage(label)}
                  className="w-full glass-card p-4 text-left font-semibold text-slate-800 hover:bg-white/60 active:scale-[0.98] transition-all shadow-md hover:shadow-lg flex items-center"
                >
                  <span>{label}</span>
                </button>
              ))}

              <button
                onClick={() => setCurrentMenu('main')}
                className="w-full glass-card p-4 text-center font-bold text-slate-700 hover:bg-white/70 active:scale-[0.98] transition-all shadow-md hover:shadow-lg"
              >
                🔙 Назад
              </button>
            </>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-sand font-sans text-slate-900 pb-24 overflow-x-hidden selection:bg-emerald-100">
      {/* Immersive Header */}
      <header className="premium-gradient text-white pt-8 pb-12 px-6 rounded-b-[2.5rem] shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -mr-20 -mt-20 blur-3xl" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-emerald-400/10 rounded-full -ml-10 -mb-10 blur-2xl" />

        <div className="relative z-10 flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight">Отель «ГОРА»</h1>
            <p className="text-emerald-100/80 font-medium flex items-center mt-1">
              <span className="mr-1">📍</span> Сортавала, Карелия
            </p>
          </div>
          <div className="w-12 h-12 bg-white/20 backdrop-blur-md rounded-2xl flex items-center justify-center border border-white/30">
            <span className="text-2xl">🌲</span>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="-mt-8 px-4 relative z-20">
        {activeTab === 'home' && (
          <div className="space-y-6 animate-fade-in">
            <div className="glass-card p-6 shadow-sm">
              <h2 className="text-2xl font-bold mb-3 text-emerald-900">Добро пожаловать в Карелию</h2>
              <p className="text-slate-600 leading-relaxed">
                Погрузитесь в атмосферу спокойствия и природной гармонии на берегу Ладожских шхер.
              </p>
            </div>

            <div className="relative group overflow-hidden rounded-3xl shadow-lg h-60">
              <img
                src="https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=1000&q=90"
                alt="Hotel Landscape"
                className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent flex items-end p-6">
                <p className="text-white font-semibold text-lg">Ваш идеальный отдых начинается здесь</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="glass-card p-4 flex flex-col items-center text-center">
                <div className="w-10 h-10 bg-emerald-100 text-emerald-700 rounded-full flex items-center justify-center mb-2">⭐</div>
                <span className="text-sm font-bold">Высший сервис</span>
              </div>
              <div className="glass-card p-4 flex flex-col items-center text-center">
                <div className="w-10 h-10 bg-sky-100 text-sky-700 rounded-full flex items-center justify-center mb-2">🌊</div>
                <span className="text-sm font-bold">Ладога рядом</span>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'services' && (
          <div className="space-y-6 animate-fade-in">
            <div className="flex justify-between items-end px-2">
              <h2 className="text-2xl font-bold text-slate-800">Активный отдых</h2>
              <span className="text-emerald-700 text-sm font-bold">Все услуги</span>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {[
                { id: 'sup', name: 'Сап-борды', icon: '🏄', price: '800₽', color: 'bg-amber-50' },
                { id: 'boats', name: 'Лодки', icon: '⛵', price: '1500₽', color: 'bg-blue-50' },
                { id: 'sauna', name: 'Баня', icon: '🧖‍♀️', price: '3000₽', color: 'bg-red-50' },
                { id: 'houseboat', name: 'Хаусбот', icon: '🏠', price: '2500₽', color: 'bg-indigo-50' },
              ].map((service) => (
                <button
                  key={service.id}
                  onClick={() => handleServiceClick(service.name)}
                  className={`glass-card p-5 group transition-all duration-300 active:scale-95 text-left border-transparent hover:border-emerald-200`}
                >
                  <div className={`w-12 h-12 ${service.color} rounded-2xl flex items-center justify-center text-2xl mb-4 shadow-inner`}>
                    {service.icon}
                  </div>
                  <h3 className="font-bold text-slate-800 mb-1">{service.name}</h3>
                  <p className="text-emerald-700 font-extrabold text-sm">{service.price}</p>
                </button>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'restaurant' && (
          <div className="space-y-6 animate-fade-in">
            <h2 className="text-2xl font-bold px-2 text-slate-800">Ресторан «ГОРА»</h2>

            <div className="glass-card overflow-hidden transition-all duration-500 hover:shadow-md">
              <div className="h-44 relative">
                <img
                  src="https://images.unsplash.com/photo-1552566626-52f8b828add9?auto=format&fit=crop&w=1000&q=90"
                  alt="Restaurant dish"
                  className="w-full h-full object-cover"
                />
                <div className="absolute top-4 right-4 bg-white/90 backdrop-blur shadow-lg px-3 py-1 rounded-full text-xs font-bold text-emerald-900 border border-emerald-100">
                  Открыто до 23:00
                </div>
              </div>

              <div className="p-5 space-y-4">
                <div className="space-y-3">
                  {[
                    { name: 'Завтрак «Шведский стол»', price: '650₽', icon: '🍳' },
                    { name: 'Уха Карельская', price: '550₽', icon: '🐟' },
                    { name: 'Оленина с брусникой', price: '1200₽', icon: '🦌' },
                  ].map((item, idx) => (
                    <div key={idx} className="flex justify-between items-center group cursor-pointer p-2 -mx-2 rounded-xl hover:bg-emerald-50/50 transition-colors">
                      <div className="flex items-center">
                        <span className="mr-3 text-lg opacity-80">{item.icon}</span>
                        <span className="font-medium text-slate-700">{item.name}</span>
                      </div>
                      <span className="font-bold text-emerald-800">{item.price}</span>
                    </div>
                  ))}
                </div>

                <button
                  onClick={() => handleServiceClick('Заказ в ресторане')}
                  className="w-full premium-gradient text-white py-4 rounded-2xl font-bold shadow-lg shadow-emerald-900/20 active:scale-[0.98] transition-all"
                >
                  Заказать доставку в номер
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Modern Bottom Navigation */}
      <nav className="fixed bottom-6 left-4 right-4 glass-nav rounded-[2rem] p-2 flex justify-between shadow-2xl z-50 ring-1 ring-black/5">
        {[
          { id: 'home', label: 'Отель', icon: '🏨' },
          { id: 'services', label: 'Услуги', icon: '🎯' },
          { id: 'restaurant', label: 'Ресторан', icon: '🍽' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 flex flex-col items-center py-3 rounded-2xl transition-all duration-300 ${activeTab === tab.id
              ? 'text-emerald-900 bg-emerald-100/80 shadow-inner'
              : 'text-slate-400 hover:text-slate-600'
              }`}
          >
            <span className={`text-2xl mb-1 transition-transform duration-300 ${activeTab === tab.id ? 'scale-110 mb-0.5' : ''}`}>
              {tab.icon}
            </span>
            <span className={`text-[10px] font-bold tracking-wider uppercase transition-all duration-300 ${activeTab === tab.id ? 'opacity-100' : 'opacity-60'}`}>
              {tab.label}
            </span>
          </button>
        ))}
      </nav>
    </div>
  );
};

export default App;