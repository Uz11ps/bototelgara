import React, { useState, useEffect } from 'react';
import { fetchMenuItems, MenuItem } from '../../data/mockData';
import { Cart } from './Cart';

interface MenuProps {
    onAddToCart: (itemId: number) => void;
}

export const Menu: React.FC<MenuProps> = () => {
    const [items, setItems] = useState<MenuItem[]>([]);
    const [activeCategory, setActiveCategory] = useState<string>('all');
    const [cart, setCart] = useState<{ [itemId: number]: number }>({});
    const [isCartOpen, setIsCartOpen] = useState(false);
    const [loading, setLoading] = useState(true);

    // Breakfast availability: check if current server time <= 17:45
    const [breakfastAvailable, setBreakfastAvailable] = useState(true);

    useEffect(() => {
        fetchMenuItems()
            .then(data => { setItems(data); setLoading(false); })
            .catch(() => setLoading(false));

        // Check breakfast time (Moscow TZ = UTC+3)
        const checkBreakfastTime = () => {
            const now = new Date();
            // Get Moscow time
            const msk = new Date(now.toLocaleString('en-US', { timeZone: 'Europe/Moscow' }));
            const hours = msk.getHours();
            const minutes = msk.getMinutes();
            const totalMinutes = hours * 60 + minutes;
            // Available until 17:45 (1065 minutes)
            setBreakfastAvailable(totalMinutes <= 17 * 60 + 45);
        };
        checkBreakfastTime();
        const timer = setInterval(checkBreakfastTime, 60000);
        return () => clearInterval(timer);
    }, []);

    const categories: { id: string; label: string }[] = [
        { id: 'all', label: 'Всё' },
        { id: 'breakfast', label: '🍳 Завтраки' },
        { id: 'lunch', label: '🍽 Обеды' },
        { id: 'dinner', label: '🌙 Ужины' },
    ];

    const filteredItems = items.filter(item => {
        const cat = item.category_type || item.category;
        if (activeCategory !== 'all' && cat !== activeCategory) return false;
        // Hide breakfast items if past 17:45
        if (cat === 'breakfast' && !breakfastAvailable) return false;
        return true;
    });

    const cartTotalQty = Object.values(cart).reduce((a, b) => a + b, 0);

    const updateCart = (itemId: number, newQty: number) => {
        setCart(prev => {
            const next = { ...prev };
            if (newQty <= 0) {
                delete next[itemId];
            } else {
                next[itemId] = newQty;
            }
            return next;
        });
    };

    const addToCart = (itemId: number) => {
        setCart(prev => ({
            ...prev,
            [itemId]: (prev[itemId] || 0) + 1
        }));
    };

    if (loading) {
        return (
            <div className="flex justify-center items-center py-20 animate-fade-in">
                <div className="w-8 h-8 border-4 border-emerald-200 border-t-emerald-600 rounded-full animate-spin"></div>
            </div>
        );
    }

    return (
        <div className="pb-24 animate-fade-in relative min-h-screen">
            <div className="sticky top-0 z-20 bg-sand/95 backdrop-blur-sm py-4 px-2 -mx-4 overflow-x-auto whitespace-nowrap scrollbar-hide mb-4 shadow-sm">
                <div className="px-4 flex space-x-2">
                    {categories.map(cat => {
                        // Hide breakfast tab if not available
                        if (cat.id === 'breakfast' && !breakfastAvailable) return null;
                        return (
                            <button
                                key={cat.id}
                                onClick={() => setActiveCategory(cat.id)}
                                className={`px-4 py-2 rounded-full font-bold text-sm transition-all ${activeCategory === cat.id
                                    ? 'bg-emerald-600 text-white shadow-md'
                                    : 'bg-white text-slate-600 hover:bg-emerald-50'
                                    }`}
                            >
                                {cat.label}
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* Breakfast time notice */}
            {!breakfastAvailable && activeCategory === 'all' && (
                <div className="mx-1 mb-4 p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-700 text-sm text-center">
                    ⏰ Заказ завтраков доступен до 17:45
                </div>
            )}

            <div className="space-y-4 px-1">
                {filteredItems.length === 0 ? (
                    <div className="text-center py-10 text-slate-400">Нет доступных блюд</div>
                ) : filteredItems.map(item => (
                    <div key={item.id} className="glass-card flex overflow-hidden p-3 gap-3">
                        {(item.imageUrl || item.image_url) && (
                            <img src={item.imageUrl || item.image_url} alt={item.name} className="w-24 h-24 rounded-xl object-cover" />
                        )}
                        <div className="flex-1 flex flex-col justify-between">
                            <div>
                                <h3 className="font-bold text-slate-800 leading-tight mb-1">{item.name}</h3>
                                {item.description && (
                                    <p className="text-xs text-slate-500 line-clamp-2 mb-2">{item.description}</p>
                                )}
                            </div>
                            <div className="flex justify-between items-end">
                                <span className="font-bold text-emerald-800 text-lg">{item.price} ₽</span>
                                {cart[item.id] ? (
                                    <div className="flex items-center bg-emerald-100 rounded-lg p-1">
                                        <button
                                            onClick={() => updateCart(item.id, cart[item.id] - 1)}
                                            className="w-7 h-7 flex items-center justify-center text-emerald-700 font-bold"
                                        >
                                            -
                                        </button>
                                        <span className="w-6 text-center font-bold text-sm">{cart[item.id]}</span>
                                        <button
                                            onClick={() => updateCart(item.id, cart[item.id] + 1)}
                                            className="w-7 h-7 flex items-center justify-center text-emerald-700 font-bold"
                                        >
                                            +
                                        </button>
                                    </div>
                                ) : (
                                    <button
                                        onClick={() => addToCart(item.id)}
                                        className="bg-slate-100 hover:bg-emerald-100 text-slate-700 hover:text-emerald-800 px-3 py-1.5 rounded-lg text-sm font-bold transition-colors"
                                    >
                                        Добавить
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Cart Floating Button */}
            {cartTotalQty > 0 && (
                <div className="fixed bottom-24 left-4 right-4 z-30">
                    <button
                        onClick={() => setIsCartOpen(true)}
                        className="w-full bg-slate-900 text-white p-4 rounded-2xl shadow-xl flex justify-between items-center"
                    >
                        <div className="flex items-center">
                            <span className="bg-emerald-500 text-white text-xs font-bold w-6 h-6 rounded-full flex items-center justify-center mr-3">
                                {cartTotalQty}
                            </span>
                            <span className="font-bold">Корзина</span>
                        </div>
                        <span className="font-bold">
                            {Object.entries(cart).reduce((sum, [id, qty]) => {
                                const item = items.find(i => i.id === Number(id));
                                return sum + (item ? item.price * qty : 0);
                            }, 0)} ₽
                        </span>
                    </button>
                </div>
            )}

            {isCartOpen && (
                <Cart
                    cart={cart}
                    items={items}
                    onUpdateCart={updateCart}
                    onClose={() => setIsCartOpen(false)}
                />
            )}
        </div>
    );
};
