import React, { useState, useEffect } from 'react';

// Mock Telegram WebApp SDK for local development
const WebApp = (window as any).Telegram?.WebApp || {
  ready: () => {},
  expand: () => {},
  sendData: (data: string) => console.log('SendData:', data),
  close: () => {},
};

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('home');

  useEffect(() => {
    WebApp.ready();
    WebApp.expand();
  }, []);

  const handleServiceClick = (service: string) => {
    WebApp.sendData(JSON.stringify({ action: 'book_service', service }));
    WebApp.close();
  };

  return (
    <div className="min-h-screen bg-gray-100 font-sans text-gray-900 pb-20">
      {/* Header */}
      <header className="bg-green-800 text-white p-6 shadow-md">
        <h1 className="text-2xl font-bold">Отель «ГОРА»</h1>
        <p className="text-sm opacity-80">Сортавала, Карелия</p>
      </header>

      {/* Content */}
      <main className="p-4">
        {activeTab === 'home' && (
          <div className="space-y-4 animate-fade-in">
            <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200">
              <h2 className="text-xl font-bold mb-2">Добро пожаловать!</h2>
              <p className="text-gray-600">Премиальный загородный отдых на берегу Ладожского озера.</p>
            </div>
            <img 
              src="https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=800&q=80" 
              alt="Hotel" 
              className="w-full h-48 object-cover rounded-xl shadow-sm"
            />
          </div>
        )}

        {activeTab === 'services' && (
          <div className="space-y-4 animate-fade-in">
            <h2 className="text-xl font-bold px-2">Дополнительные услуги</h2>
            <div className="grid grid-cols-2 gap-4">
              {[
                { id: 'sup', name: 'Сап-борды', icon: '🏄', price: '800₽' },
                { id: 'boats', name: 'Лодки', icon: '⛵', price: '1500₽' },
                { id: 'sauna', name: 'Баня', icon: '🧖‍♀️', price: '3000₽' },
                { id: 'houseboat', name: 'Хаусбот', icon: '🏠', price: '2500₽' },
              ].map((service) => (
                <button 
                  key={service.id}
                  onClick={() => handleServiceClick(service.name)}
                  className="bg-white p-4 rounded-xl shadow-sm border border-gray-200 flex flex-col items-center hover:bg-gray-50 transition-colors"
                >
                  <span className="text-3xl mb-2">{service.icon}</span>
                  <span className="font-bold">{service.name}</span>
                  <span className="text-green-700 text-sm">{service.price}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'restaurant' && (
          <div className="space-y-4 animate-fade-in">
            <h2 className="text-xl font-bold px-2">Ресторан «ГОРА»</h2>
            <div className="bg-white rounded-xl shadow-sm overflow-hidden border border-gray-200">
              <img 
                src="https://images.unsplash.com/photo-1552566626-52f8b828add9?auto=format&fit=crop&w=800&q=80" 
                alt="Restaurant" 
                className="w-full h-32 object-cover"
              />
              <div className="p-4 space-y-4">
                <div className="flex justify-between items-center border-b pb-2">
                  <span>Завтрак «Шведский стол»</span>
                  <span className="font-bold">650₽</span>
                </div>
                <div className="flex justify-between items-center border-b pb-2">
                  <span>Уха Карельская</span>
                  <span className="font-bold">550₽</span>
                </div>
                <div className="flex justify-between items-center border-b pb-2">
                  <span>Оленина с брусникой</span>
                  <span className="font-bold">1200₽</span>
                </div>
                <button 
                  onClick={() => handleServiceClick('Заказ в ресторане')}
                  className="w-full bg-green-800 text-white py-3 rounded-lg font-bold hover:bg-green-900"
                >
                  Сделать заказ
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Bottom Nav */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 flex justify-around p-2 shadow-lg">
        {[
          { id: 'home', label: 'Главная', icon: '🏨' },
          { id: 'services', label: 'Услуги', icon: '🎯' },
          { id: 'restaurant', label: 'Ресторан', icon: '🍽' },
        ].map((tab) => (
          <button 
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex flex-col items-center p-2 rounded-lg transition-colors ${activeTab === tab.id ? 'text-green-800 bg-green-50' : 'text-gray-400'}`}
          >
            <span className="text-xl">{tab.icon}</span>
            <span className="text-xs font-medium">{tab.label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
};

export default App;
