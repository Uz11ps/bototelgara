import React, { useState, useEffect } from 'react';

// Telegram WebApp SDK
const WebApp = (window as any).Telegram?.WebApp || {
  ready: () => { },
  expand: () => { },
  sendData: (data: string) => console.log('SendData:', data),
  close: () => { },
  initDataUnsafe: { user: { id: 0, first_name: 'Guest' } },
};

// Types
interface GuideItemType {
  id: number;
  category: string;
  name: string;
  description: string;
  map_url: string | null;
}

interface CompositionItem {
  name: string;
  quantity: number | null;
  unit: string | null;
}

interface MenuItemType {
  id: number;
  category: string;
  category_type: string;
  name: string;
  description: string | null;
  composition: CompositionItem[] | null;
  price: number;
  is_available: boolean;
  admin_comment: string | null;
}

interface CartEntry {
  item: MenuItemType;
  qty: number;
}

type MenuKey = 'main' | 'visual';
type ActiveTab = 'home' | 'guide' | 'restaurant' | 'cart';

const API_BASE = window.location.origin;

const GUIDE_CATEGORIES: Record<string, { label: string; icon: string }> = {
  nature: { label: 'Природа и парки', icon: '🌲' },
  cafes: { label: 'Кафе и рестораны', icon: '🍴' },
  rent: { label: 'Активный отдых', icon: '🚀' },
};

const MENU_CATEGORIES: Record<string, { label: string; icon: string }> = {
  breakfast: { label: 'Завтраки', icon: '🍳' },
  lunch: { label: 'Обеды', icon: '🍲' },
  dinner: { label: 'Ужин', icon: '🌙' },
};

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('home');
  const [currentMenu, setCurrentMenu] = useState<MenuKey>('main');

  // Data from API
  const [guideItems, setGuideItems] = useState<GuideItemType[]>([]);
  const [menuItems, setMenuItems] = useState<MenuItemType[]>([]);
  const [guideLoading, setGuideLoading] = useState(false);
  const [menuLoading, setMenuLoading] = useState(false);

  // Expanded sections
  const [expandedGuideCategories, setExpandedGuideCategories] = useState<Record<string, boolean>>({});
  const [expandedMenuCategories, setExpandedMenuCategories] = useState<Record<string, boolean>>({});
  const [expandedMenuItems, setExpandedMenuItems] = useState<Record<number, boolean>>({});

  // Cart
  const [cart, setCart] = useState<Record<number, number>>({});

  // Checkout
  const [roomNumber, setRoomNumber] = useState('');
  const [comment, setComment] = useState('');
  const [orderSubmitting, setOrderSubmitting] = useState(false);
  const [orderSuccess, setOrderSuccess] = useState<{ orderId: number; total: number } | null>(null);

  useEffect(() => {
    WebApp.ready();
    WebApp.expand();
  }, []);

  // Fetch guide data
  useEffect(() => {
    if (activeTab === 'guide' && guideItems.length === 0 && !guideLoading) {
      setGuideLoading(true);
      fetch(`${API_BASE}/api/guide`)
        .then(r => r.json())
        .then(data => {
          setGuideItems(data);
          const expanded: Record<string, boolean> = {};
          data.forEach((item: GuideItemType) => { expanded[item.category] = true; });
          setExpandedGuideCategories(expanded);
        })
        .catch(e => console.error('Guide fetch error:', e))
        .finally(() => setGuideLoading(false));
    }
  }, [activeTab]);

  // Fetch menu data
  useEffect(() => {
    if ((activeTab === 'restaurant' || activeTab === 'cart') && menuItems.length === 0 && !menuLoading) {
      setMenuLoading(true);
      fetch(`${API_BASE}/api/menu`)
        .then(r => r.json())
        .then(data => {
          setMenuItems(data);
          const expanded: Record<string, boolean> = {};
          data.forEach((item: MenuItemType) => { expanded[item.category] = true; });
          setExpandedMenuCategories(expanded);
        })
        .catch(e => console.error('Menu fetch error:', e))
        .finally(() => setMenuLoading(false));
    }
  }, [activeTab]);

  const sendMenuMessage = (text: string) => {
    WebApp.sendData(JSON.stringify({ action: 'suggested_question', text }));
  };

  const toggleGuideCategory = (cat: string) => {
    setExpandedGuideCategories((prev: Record<string, boolean>) => ({ ...prev, [cat]: !prev[cat] }));
  };
  const toggleMenuCategory = (cat: string) => {
    setExpandedMenuCategories((prev: Record<string, boolean>) => ({ ...prev, [cat]: !prev[cat] }));
  };
  const toggleMenuItem = (id: number) => {
    setExpandedMenuItems((prev: Record<number, boolean>) => ({ ...prev, [id]: !prev[id] }));
  };

  // Cart helpers
  const addToCart = (itemId: number) => {
    setCart((prev: Record<number, number>) => ({ ...prev, [itemId]: (prev[itemId] || 0) + 1 }));
  };
  const removeFromCart = (itemId: number) => {
    setCart((prev: Record<number, number>) => {
      const newQty = (prev[itemId] || 0) - 1;
      if (newQty <= 0) {
        const next = { ...prev };
        delete next[itemId];
        return next;
      }
      return { ...prev, [itemId]: newQty };
    });
  };
  const clearCart = () => setCart({});

  const cartItemCount = Object.values(cart).reduce((s: number, q: number) => s + q, 0);

  const getCartEntries = (): CartEntry[] => {
    const entries: CartEntry[] = [];
    for (const [idStr, qty] of Object.entries(cart)) {
      const item = menuItems.find(m => m.id === Number(idStr));
      if (item && qty > 0) entries.push({ item, qty });
    }
    return entries;
  };

  const cartTotal = getCartEntries().reduce((s, e) => s + e.item.price * e.qty, 0);

  // Submit order
  const submitOrder = async () => {
    if (cartItemCount === 0 || !roomNumber.trim()) return;
    setOrderSubmitting(true);

    const telegramUser = WebApp.initDataUnsafe?.user;
    const telegramId = telegramUser?.id ? String(telegramUser.id) : '';
    const guestName = telegramUser?.first_name
      ? `${telegramUser.first_name}${telegramUser.last_name ? ' ' + telegramUser.last_name : ''}`
      : 'Гость';

    const body = {
      guest_name: guestName,
      room_number: roomNumber.trim(),
      comment: comment.trim() || null,
      items: Object.entries(cart).map(([id, qty]) => ({ id: Number(id), qty })),
      telegram_id: telegramId || null,
    };

    try {
      const resp = await fetch(`${API_BASE}/api/orders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (resp.ok) {
        const data = await resp.json();
        setOrderSuccess({ orderId: data.order_id, total: data.total });
        clearCart();
        setRoomNumber('');
        setComment('');
      } else {
        alert('Ошибка при оформлении заказа. Попробуйте снова.');
      }
    } catch {
      alert('Ошибка сети. Проверьте соединение.');
    } finally {
      setOrderSubmitting(false);
    }
  };

  const groupByCategory = <T extends { category: string }>(items: T[]): Record<string, T[]> => {
    return items.reduce((acc, item) => {
      if (!acc[item.category]) acc[item.category] = [];
      acc[item.category].push(item);
      return acc;
    }, {} as Record<string, T[]>);
  };

  const switchTab = (tab: ActiveTab) => {
    setActiveTab(tab);
    setCurrentMenu('main');
    if (tab !== 'cart') setOrderSuccess(null);
  };

  // ══════════════════════════════════════════════
  // HOME SCREEN
  // ══════════════════════════════════════════════
  if (activeTab === 'home') {
    return (
      <div className="min-h-screen bg-sand font-sans flex flex-col justify-center items-center p-6 animate-fade-in relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-400/10 rounded-full -mr-20 -mt-20 blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-emerald-600/10 rounded-full -ml-10 -mb-10 blur-2xl pointer-events-none" />

        <div className="text-center mb-10 z-10">
          <h1 className="text-3xl font-extrabold text-emerald-900 mb-2 tracking-tight">Отель «ГОРА»</h1>
          <p className="text-slate-600 font-medium">
            {currentMenu === 'main' && 'Чем мы можем вам помочь?'}
            {currentMenu === 'visual' && 'Визуальное меню'}
          </p>
        </div>

        <div className="w-full max-w-sm space-y-4 z-10">
          {currentMenu === 'main' && (
            <>
              <button onClick={() => sendMenuMessage('Я планирую поездку')}
                className="w-full glass-card p-5 text-left font-bold text-slate-800 hover:bg-white/60 active:scale-[0.98] transition-all shadow-md hover:shadow-lg flex items-center group">
                <span className="text-2xl mr-4 group-hover:scale-110 transition-transform duration-300">✈️</span>
                <span>Я планирую поездку</span>
              </button>
              <button onClick={() => sendMenuMessage('Я уже проживаю в отеле')}
                className="w-full glass-card p-5 text-left font-bold text-slate-800 hover:bg-white/60 active:scale-[0.98] transition-all shadow-md hover:shadow-lg flex items-center group">
                <span className="text-2xl mr-4 group-hover:scale-110 transition-transform duration-300">🏨</span>
                <span>Я уже проживаю в отеле</span>
              </button>
              <button onClick={() => setCurrentMenu('visual')}
                className="w-full glass-card p-5 text-left font-bold text-slate-800 hover:bg-white/60 active:scale-[0.98] transition-all shadow-md hover:shadow-lg flex items-center group">
                <span className="text-2xl mr-4 group-hover:scale-110 transition-transform duration-300">🗓️</span>
                <span>Визуальное меню 🗓️</span>
              </button>
            </>
          )}
          {currentMenu === 'visual' && (
            <>
              {['🏨 Забронировать номер','🛏️ Номера и цены','🌲 Об отеле','🎉 Мероприятия и банкеты','📍 Как добраться','❓ Вопросы и ответы','🍽️ Ресторан','📞 Связаться с администратором'].map((label) => (
                <button key={label} onClick={() => sendMenuMessage(label)}
                  className="w-full glass-card p-4 text-left font-semibold text-slate-800 hover:bg-white/60 active:scale-[0.98] transition-all shadow-md hover:shadow-lg flex items-center">
                  <span>{label}</span>
                </button>
              ))}
              <button onClick={() => setCurrentMenu('main')}
                className="w-full glass-card p-4 text-center font-bold text-slate-700 hover:bg-white/70 active:scale-[0.98] transition-all shadow-md hover:shadow-lg">
                🔙 Назад
              </button>
            </>
          )}
        </div>

        {/* Bottom nav */}
        <BottomNav activeTab={activeTab} cartCount={cartItemCount} onSwitch={switchTab} />
      </div>
    );
  }

  // ══════════════════════════════════════════════
  // INNER PAGES (guide / restaurant / cart)
  // ══════════════════════════════════════════════
  const guideGrouped = groupByCategory(guideItems);
  const menuGrouped = groupByCategory(menuItems.filter(m => m.is_available));
  const cartEntries = getCartEntries();

  return (
    <div className="min-h-screen bg-sand font-sans text-slate-900 pb-28 overflow-x-hidden selection:bg-emerald-100">
      {/* Header */}
      <header className="premium-gradient text-white pt-6 pb-6 px-6 rounded-b-[2rem] shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -mr-20 -mt-20 blur-3xl" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-emerald-400/10 rounded-full -ml-10 -mb-10 blur-2xl" />
        <div className="relative z-10 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight">Отель «ГОРА»</h1>
            <p className="text-emerald-100/80 text-sm font-medium flex items-center mt-0.5">
              <span className="mr-1">📍</span> Сортавала, Карелия
            </p>
          </div>
          <div className="w-10 h-10 bg-white/20 backdrop-blur-md rounded-xl flex items-center justify-center border border-white/30">
            <span className="text-xl">🌲</span>
          </div>
        </div>
      </header>

      {/* Main Content — shifted down less aggressively */}
      <main className="mt-4 px-4 relative z-20">

        {/* ══════ GUIDE TAB ══════ */}
        {activeTab === 'guide' && (
          <div className="space-y-4 animate-fade-in">
            <div className="glass-card p-4 shadow-sm">
              <h2 className="text-xl font-bold text-emerald-900 flex items-center">
                <span className="mr-2">🗺️</span> Гид по Сортавала
              </h2>
              <p className="text-slate-500 text-sm mt-1">Красивые места и развлечения рядом с отелем</p>
            </div>

            {guideLoading ? (
              <div className="flex justify-center py-12">
                <div className="w-8 h-8 border-3 border-emerald-300 border-t-emerald-700 rounded-full animate-spin" />
              </div>
            ) : (
              Object.entries(GUIDE_CATEGORIES).map(([catKey, catInfo]) => {
                const items = guideGrouped[catKey] || [];
                if (items.length === 0) return null;
                const isExpanded = expandedGuideCategories[catKey];
                return (
                  <div key={catKey} className="glass-card overflow-hidden shadow-sm">
                    <button onClick={() => toggleGuideCategory(catKey)}
                      className="w-full flex items-center justify-between p-4 hover:bg-white/50 transition-colors">
                      <div className="flex items-center">
                        <span className="text-xl mr-3">{catInfo.icon}</span>
                        <span className="font-bold text-slate-800 text-lg">{catInfo.label}</span>
                        <span className="ml-2 text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">{items.length}</span>
                      </div>
                      <span className={`text-slate-400 transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}>▼</span>
                    </button>
                    {isExpanded && (
                      <div className="border-t border-white/40">
                        {items.map((item, idx) => (
                          <div key={item.id} className={`p-4 ${idx < items.length - 1 ? 'border-b border-white/30' : ''} hover:bg-emerald-50/30 transition-colors`}>
                            <h3 className="font-bold text-slate-800 mb-1">{item.name}</h3>
                            <p className="text-slate-500 text-sm leading-relaxed mb-2">{item.description}</p>
                            {item.map_url && (
                              <a href={item.map_url} target="_blank" rel="noopener noreferrer"
                                className="inline-flex items-center text-emerald-700 font-semibold text-sm hover:text-emerald-900 transition-colors">
                                <span className="mr-1">📍</span> Показать на карте <span className="ml-1">→</span>
                              </a>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        )}

        {/* ══════ MENU TAB ══════ */}
        {activeTab === 'restaurant' && (
          <div className="space-y-4 animate-fade-in">
            <div className="glass-card p-4 shadow-sm">
              <h2 className="text-xl font-bold text-emerald-900 flex items-center">
                <span className="mr-2">🍽</span> Меню ресторана
              </h2>
              <p className="text-slate-500 text-sm mt-1">Нажмите + чтобы добавить блюдо в корзину</p>
            </div>

            {menuLoading ? (
              <div className="flex justify-center py-12">
                <div className="w-8 h-8 border-3 border-emerald-300 border-t-emerald-700 rounded-full animate-spin" />
              </div>
            ) : (
              Object.entries(MENU_CATEGORIES).map(([catKey, catInfo]) => {
                const items = menuGrouped[catKey] || [];
                if (items.length === 0) return null;
                const isExpanded = expandedMenuCategories[catKey];
                return (
                  <div key={catKey} className="glass-card overflow-hidden shadow-sm">
                    <button onClick={() => toggleMenuCategory(catKey)}
                      className="w-full flex items-center justify-between p-4 hover:bg-white/50 transition-colors">
                      <div className="flex items-center">
                        <span className="text-xl mr-3">{catInfo.icon}</span>
                        <span className="font-bold text-slate-800 text-lg">{catInfo.label}</span>
                        <span className="ml-2 text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">{items.length}</span>
                      </div>
                      <span className={`text-slate-400 transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}>▼</span>
                    </button>

                    {isExpanded && (
                      <div className="border-t border-white/40">
                        {items.map((item, idx) => {
                          const isItemExpanded = expandedMenuItems[item.id];
                          const hasComposition = item.composition && item.composition.length > 0;
                          const inCart = cart[item.id] || 0;

                          return (
                            <div key={item.id} className={`${idx < items.length - 1 ? 'border-b border-white/30' : ''}`}>
                              <div className="p-4">
                                <div className="flex justify-between items-start">
                                  <button onClick={() => hasComposition && toggleMenuItem(item.id)}
                                    className={`flex-1 text-left pr-3 ${hasComposition ? 'cursor-pointer' : 'cursor-default'}`}>
                                    <h3 className="font-bold text-slate-800">{item.name}</h3>
                                    {item.description && <p className="text-slate-500 text-sm mt-0.5">{item.description}</p>}
                                    {item.admin_comment && (
                                      <span className="inline-block mt-1 text-xs font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full">{item.admin_comment}</span>
                                    )}
                                    {hasComposition && (
                                      <span className={`inline-block text-xs text-slate-400 mt-1 transition-transform duration-300 ${isItemExpanded ? 'rotate-180' : ''}`}>▼ состав</span>
                                    )}
                                  </button>
                                  <div className="flex flex-col items-end gap-2 ml-2">
                                    <span className="font-extrabold text-emerald-800 whitespace-nowrap">{item.price}₽</span>
                                    {/* Add to cart controls */}
                                    <div className="flex items-center gap-1">
                                      {inCart > 0 && (
                                        <>
                                          <button onClick={() => removeFromCart(item.id)}
                                            className="w-8 h-8 rounded-full bg-red-50 text-red-600 font-bold text-lg flex items-center justify-center active:scale-90 transition-transform">
                                            −
                                          </button>
                                          <span className="w-6 text-center font-bold text-sm">{inCart}</span>
                                        </>
                                      )}
                                      <button onClick={() => addToCart(item.id)}
                                        className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-700 font-bold text-lg flex items-center justify-center active:scale-90 transition-transform shadow-sm">
                                        +
                                      </button>
                                    </div>
                                  </div>
                                </div>
                              </div>

                              {/* Composition */}
                              {isItemExpanded && hasComposition && (
                                <div className="px-4 pb-4 -mt-1">
                                  <div className="bg-emerald-50/50 rounded-xl p-3 border border-emerald-100/50">
                                    <p className="text-xs font-bold text-emerald-800 mb-2 uppercase tracking-wider">Состав</p>
                                    <div className="space-y-1">
                                      {item.composition!.map((comp, cIdx) => (
                                        <div key={cIdx} className="flex justify-between items-center text-sm">
                                          <span className="text-slate-600">{comp.name}</span>
                                          {comp.quantity && comp.unit && (
                                            <span className="text-slate-400 text-xs font-medium">{comp.quantity} {comp.unit}</span>
                                          )}
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })
            )}

            {/* Go to cart button */}
            {cartItemCount > 0 && (
              <button onClick={() => switchTab('cart')}
                className="w-full premium-gradient text-white py-4 rounded-2xl font-bold shadow-lg shadow-emerald-900/20 active:scale-[0.98] transition-all flex items-center justify-center gap-2">
                <span>🛒</span>
                <span>Корзина · {cartItemCount} шт · {cartTotal}₽</span>
              </button>
            )}
          </div>
        )}

        {/* ══════ CART TAB ══════ */}
        {activeTab === 'cart' && (
          <div className="space-y-4 animate-fade-in">

            {/* Order success screen */}
            {orderSuccess ? (
              <div className="glass-card p-6 text-center space-y-4 shadow-sm">
                <div className="text-5xl">✅</div>
                <h2 className="text-2xl font-bold text-emerald-900">Заказ оформлен!</h2>
                <p className="text-slate-600">
                  Заказ <span className="font-bold">#{orderSuccess.orderId}</span> на сумму <span className="font-bold">{orderSuccess.total}₽</span> принят.
                </p>
                <p className="text-slate-500 text-sm">Вам придёт уведомление в Telegram с подтверждением. Мы свяжемся для уточнения времени доставки.</p>
                <button onClick={() => { setOrderSuccess(null); switchTab('restaurant'); }}
                  className="w-full premium-gradient text-white py-3 rounded-2xl font-bold shadow-lg active:scale-[0.98] transition-all mt-4">
                  Вернуться к меню
                </button>
              </div>
            ) : cartEntries.length === 0 ? (
              <div className="glass-card p-6 text-center space-y-4 shadow-sm">
                <div className="text-5xl">🛒</div>
                <h2 className="text-xl font-bold text-slate-700">Корзина пуста</h2>
                <p className="text-slate-500 text-sm">Добавьте блюда из меню</p>
                <button onClick={() => switchTab('restaurant')}
                  className="w-full premium-gradient text-white py-3 rounded-2xl font-bold shadow-lg active:scale-[0.98] transition-all">
                  Перейти к меню
                </button>
              </div>
            ) : (
              <>
                <div className="glass-card p-4 shadow-sm">
                  <h2 className="text-xl font-bold text-emerald-900 flex items-center">
                    <span className="mr-2">🛒</span> Ваша корзина
                  </h2>
                </div>

                {/* Cart items */}
                <div className="glass-card overflow-hidden shadow-sm">
                  {cartEntries.map((entry, idx) => (
                    <div key={entry.item.id} className={`p-4 flex justify-between items-center ${idx < cartEntries.length - 1 ? 'border-b border-white/30' : ''}`}>
                      <div className="flex-1 pr-3">
                        <h3 className="font-bold text-slate-800 text-sm">{entry.item.name}</h3>
                        <p className="text-emerald-700 font-bold text-sm mt-0.5">{entry.item.price}₽ × {entry.qty} = {entry.item.price * entry.qty}₽</p>
                      </div>
                      <div className="flex items-center gap-1">
                        <button onClick={() => removeFromCart(entry.item.id)}
                          className="w-8 h-8 rounded-full bg-red-50 text-red-600 font-bold text-lg flex items-center justify-center active:scale-90 transition-transform">
                          −
                        </button>
                        <span className="w-6 text-center font-bold text-sm">{entry.qty}</span>
                        <button onClick={() => addToCart(entry.item.id)}
                          className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-700 font-bold text-lg flex items-center justify-center active:scale-90 transition-transform">
                          +
                        </button>
                      </div>
                    </div>
                  ))}
                  {/* Total */}
                  <div className="p-4 bg-emerald-50/40 border-t border-emerald-100/50 flex justify-between items-center">
                    <span className="font-bold text-slate-700">Итого:</span>
                    <span className="font-extrabold text-xl text-emerald-800">{cartTotal}₽</span>
                  </div>
                </div>

                {/* Checkout form */}
                <div className="glass-card p-4 shadow-sm space-y-4">
                  <h3 className="font-bold text-slate-800 flex items-center">
                    <span className="mr-2">📋</span> Оформление заказа
                  </h3>
                  <div>
                    <label className="block text-sm font-semibold text-slate-600 mb-1">Номер комнаты *</label>
                    <input
                      type="text"
                      value={roomNumber}
                      onChange={e => setRoomNumber(e.target.value)}
                      placeholder="Например: 205"
                      className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white/80 focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:border-transparent text-slate-800 placeholder-slate-400"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-600 mb-1">Комментарий</label>
                    <textarea
                      value={comment}
                      onChange={e => setComment(e.target.value)}
                      placeholder="Пожелания к заказу (необязательно)"
                      rows={3}
                      className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white/80 focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:border-transparent text-slate-800 placeholder-slate-400 resize-none"
                    />
                  </div>
                </div>

                {/* Submit */}
                <button
                  onClick={submitOrder}
                  disabled={orderSubmitting || !roomNumber.trim()}
                  className={`w-full py-4 rounded-2xl font-bold shadow-lg active:scale-[0.98] transition-all flex items-center justify-center gap-2
                    ${!roomNumber.trim() ? 'bg-slate-300 text-slate-500 cursor-not-allowed' : 'premium-gradient text-white shadow-emerald-900/20'}`}>
                  {orderSubmitting ? (
                    <span>Оформляем...</span>
                  ) : (
                    <>
                      <span>Оформить заказ</span>
                      <span>· {cartTotal}₽</span>
                    </>
                  )}
                </button>

                {/* Clear cart */}
                <button onClick={clearCart}
                  className="w-full py-3 rounded-2xl font-semibold text-red-500 bg-red-50/60 active:scale-[0.98] transition-all text-sm">
                  Очистить корзину
                </button>
              </>
            )}
          </div>
        )}
      </main>

      {/* Bottom Navigation */}
      <BottomNav activeTab={activeTab} cartCount={cartItemCount} onSwitch={switchTab} />
    </div>
  );
};

// ══════════════════════════════════════════════
// Bottom Navigation Component
// ══════════════════════════════════════════════
const BottomNav: React.FC<{ activeTab: ActiveTab; cartCount: number; onSwitch: (tab: ActiveTab) => void }> = ({ activeTab, cartCount, onSwitch }) => {
  const tabs: { id: ActiveTab; label: string; icon: string }[] = [
    { id: 'home', label: 'Главная', icon: '🏨' },
    { id: 'guide', label: 'Гид', icon: '🗺️' },
    { id: 'restaurant', label: 'Меню', icon: '🍽' },
    { id: 'cart', label: 'Корзина', icon: '🛒' },
  ];

  return (
    <nav className="fixed bottom-6 left-4 right-4 glass-nav rounded-[2rem] p-2 flex justify-between shadow-2xl z-50 ring-1 ring-black/5">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onSwitch(tab.id)}
          className={`flex-1 flex flex-col items-center py-3 rounded-2xl transition-all duration-300 relative ${activeTab === tab.id
            ? 'text-emerald-900 bg-emerald-100/80 shadow-inner'
            : 'text-slate-400 hover:text-slate-600'
            }`}
        >
          <span className={`text-xl mb-0.5 transition-transform duration-300 ${activeTab === tab.id ? 'scale-110' : ''}`}>
            {tab.icon}
          </span>
          {tab.id === 'cart' && cartCount > 0 && (
            <span className="absolute -top-1 right-1/4 bg-red-500 text-white text-[9px] font-bold w-5 h-5 rounded-full flex items-center justify-center shadow-sm">
              {cartCount > 9 ? '9+' : cartCount}
            </span>
          )}
          <span className={`text-[9px] font-bold tracking-wider uppercase transition-all duration-300 ${activeTab === tab.id ? 'opacity-100' : 'opacity-60'}`}>
            {tab.label}
          </span>
        </button>
      ))}
    </nav>
  );
};

export default App;
