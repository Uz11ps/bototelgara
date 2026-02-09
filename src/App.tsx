import React, { useState, useEffect } from 'react';
import Guide from './components/Guide';
import Restaurant, { MenuItem } from './components/Restaurant';
import Cart, { CartItem } from './components/Cart';

// Telegram WebApp SDK (fallback for local dev)
const WebApp = (window as any).Telegram?.WebApp || {
  ready: () => {},
  expand: () => {},
  sendData: (data: string) => console.log('SendData:', data),
  close: () => {},
  initDataUnsafe: { user: { id: 0, first_name: 'Guest', last_name: '' } },
};

// API base URL (same origin)
const API_BASE = window.location.origin;

type Tab = 'guide' | 'menu';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('guide');
  const [cart, setCart] = useState<CartItem[]>([]);
  const [showCart, setShowCart] = useState(false);
  const [orderSent, setOrderSent] = useState(false);
  const [ordering, setOrdering] = useState(false);
  const [orderError, setOrderError] = useState('');

  useEffect(() => {
    WebApp.ready();
    WebApp.expand();
  }, []);

  /* ---- Cart logic ---- */
  const addToCart = (item: MenuItem) => {
    setCart(prev => {
      const existing = prev.find(i => i.id === item.id);
      if (existing) {
        return prev.map(i =>
          i.id === item.id ? { ...i, quantity: i.quantity + 1 } : i
        );
      }
      return [...prev, { ...item, quantity: 1 }];
    });
  };

  const updateQuantity = (id: number, delta: number) => {
    setCart(prev =>
      prev
        .map(i => {
          if (i.id !== id) return i;
          const newQty = i.quantity + delta;
          return newQty <= 0 ? null : { ...i, quantity: newQty };
        })
        .filter(Boolean) as CartItem[]
    );
  };

  const handleOrder = async (room: string, comment: string) => {
    if (ordering) return;
    setOrdering(true);
    setOrderError('');

    const user = WebApp.initDataUnsafe?.user;
    const guestName = user ? [user.first_name, user.last_name].filter(Boolean).join(' ') : 'Гость';
    const telegramId = user?.id ? String(user.id) : undefined;
    
    console.log('Order data:', { user, telegramId, guestName });

    const body = {
      guest_name: guestName,
      room_number: room.trim(),
      comment: comment.trim() || null,
      items: cart.map(i => ({ id: i.id, qty: i.quantity })),
      telegram_id: telegramId,
    };

    try {
      const res = await fetch(`${API_BASE}/api/orders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        throw new Error(`Ошибка сервера: ${res.status}`);
      }

      setCart([]);
      setShowCart(false);
      setOrderSent(true);
      // Close mini-app after showing confirmation
      setTimeout(() => WebApp.close(), 2000);
    } catch (err: any) {
      setOrderError(err.message || 'Не удалось оформить заказ');
    } finally {
      setOrdering(false);
    }
  };

  const cartCount = cart.reduce((s, i) => s + i.quantity, 0);

  /* ---- Order confirmation screen ---- */
  if (orderSent) {
    return (
      <div className="min-h-screen bg-[#fdfcf7] flex flex-col items-center justify-center p-8 animate-fade-in">
        <div className="text-6xl mb-4">✅</div>
        <h1 className="text-2xl font-extrabold text-emerald-900 mb-2">Заказ отправлен!</h1>
        <p className="text-slate-500 text-center">
          Проверьте чат с ботом — вам придёт подтверждение заказа.
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#fdfcf7] font-sans text-slate-900 pb-24 overflow-x-hidden selection:bg-emerald-100">
      {/* Header */}
      <header className="premium-gradient text-white pt-7 pb-10 px-5 rounded-b-[2rem] shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -mr-20 -mt-20 blur-3xl" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-emerald-400/10 rounded-full -ml-10 -mb-10 blur-2xl" />
        <div className="relative z-10 flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight">Отель «ГОРА»</h1>
            <p className="text-emerald-100/80 text-sm font-medium flex items-center mt-1">
              <span className="mr-1">📍</span> Сортавала, Карелия
            </p>
          </div>
          <div className="w-11 h-11 bg-white/20 backdrop-blur-md rounded-2xl flex items-center justify-center border border-white/30">
            <span className="text-xl">🌲</span>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="mt-2 px-4 relative z-20">
        {activeTab === 'guide' && <Guide />}
        {activeTab === 'menu' && (
          <Restaurant
            onAddToCart={addToCart}
            cartCount={cartCount}
            onOpenCart={() => setShowCart(true)}
          />
        )}
      </main>

      {/* Cart overlay */}
      {showCart && (
        <div className="fixed inset-0 z-50 flex items-end justify-center">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            onClick={() => setShowCart(false)}
          />
          {/* Cart sheet */}
          <div className="relative w-full max-w-lg mx-4 mb-4 animate-slide-up">
            {orderError && (
              <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-2 mb-2 text-center">
                {orderError}
              </div>
            )}
            <Cart
              items={cart}
              onUpdateQuantity={updateQuantity}
              onClose={() => setShowCart(false)}
              onOrder={handleOrder}
            />
          </div>
        </div>
      )}

      {/* Bottom navigation */}
      <nav className="fixed bottom-0 left-0 right-0 glass-nav px-2 pt-1 pb-[env(safe-area-inset-bottom,8px)] flex justify-around shadow-[0_-4px_30px_rgba(0,0,0,0.08)] z-40">
        {([
          { id: 'guide' as Tab, label: 'Гид', icon: '🗺' },
          { id: 'menu' as Tab, label: 'Меню', icon: '🍽' },
        ]).map(tab => (
          <button
            key={tab.id}
            onClick={() => { setActiveTab(tab.id); setShowCart(false); }}
            className={`flex-1 flex flex-col items-center py-2.5 rounded-2xl transition-all duration-300 ${
              activeTab === tab.id
                ? 'text-emerald-900 bg-emerald-100/80'
                : 'text-slate-400 hover:text-slate-600'
            }`}
          >
            <span className={`text-2xl mb-0.5 transition-transform duration-300 ${activeTab === tab.id ? 'scale-110' : ''}`}>
              {tab.icon}
            </span>
            <span className={`text-[10px] font-bold tracking-wider uppercase ${activeTab === tab.id ? 'opacity-100' : 'opacity-60'}`}>
              {tab.label}
            </span>
          </button>
        ))}
      </nav>
    </div>
  );
};

export default App;
