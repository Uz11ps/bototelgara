import React, { useState, useEffect } from 'react';

interface MenuItem {
    id: number;
    name: string;
    description: string;
    price: number;
    category: string;
    badge?: string;
    composition?: string[];
}

const API_BASE = window.location.origin;

const categories = [
    { id: 'breakfast', label: '🍳 Завтрак' },
    { id: 'lunch', label: '🥗 Обед' },
    { id: 'dinner', label: '🍽 Ужин' },
];

function parseComposition(raw: any): string[] {
    if (!raw || !Array.isArray(raw)) return [];
    return raw.map((c: any) => {
        if (typeof c === 'string') return c;
        const name = c.name || '';
        if (c.quantity && c.unit) return `${name} — ${c.quantity} ${c.unit}`;
        return name;
    }).filter(Boolean);
}

interface RestaurantProps {
    onAddToCart: (item: MenuItem) => void;
    cartCount: number;
    onOpenCart: () => void;
}

const Restaurant: React.FC<RestaurantProps> = ({ onAddToCart, cartCount, onOpenCart }) => {
    const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeCategory, setActiveCategory] = useState('breakfast');
    const [expandedId, setExpandedId] = useState<number | null>(null);

    useEffect(() => {
        fetch(`${API_BASE}/api/menu`)
            .then(r => r.json())
            .then((data: any[]) => {
                const items: MenuItem[] = data
                    .filter((d: any) => d.is_available !== false)
                    .map((d: any) => ({
                        id: d.id,
                        name: d.name,
                        description: d.description || '',
                        price: d.price,
                        category: d.category || 'dinner',
                        badge: d.admin_comment || undefined,
                        composition: parseComposition(d.composition),
                    }));
                setMenuItems(items);
            })
            .catch(() => {})
            .finally(() => setLoading(false));
    }, []);

    const filtered = menuItems.filter(i => i.category === activeCategory);

    if (loading) {
        return (
            <div className="flex items-center justify-center py-20">
                <span className="text-gray-400 text-sm">Загрузка меню...</span>
            </div>
        );
    }

    return (
        <div className="space-y-5 animate-fade-in">
            <div className="flex justify-between items-center px-1">
                <h2 className="text-2xl font-bold text-emerald-900">Меню ресторана</h2>
                {cartCount > 0 && (
                    <button
                        onClick={onOpenCart}
                        className="bg-emerald-800 text-white px-4 py-2 rounded-full font-bold shadow-md flex items-center gap-2 active:scale-95 transition-transform"
                    >
                        <span>🛒</span>
                        <span>{cartCount}</span>
                    </button>
                )}
            </div>

            {/* Category tabs */}
            <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
                {categories.map(cat => (
                    <button
                        key={cat.id}
                        onClick={() => { setActiveCategory(cat.id); setExpandedId(null); }}
                        className={`whitespace-nowrap px-4 py-2 rounded-full text-sm font-bold transition-all ${
                            activeCategory === cat.id
                                ? 'bg-emerald-800 text-white shadow-md'
                                : 'bg-white/70 text-slate-600 border border-slate-200'
                        }`}
                    >
                        {cat.label}
                    </button>
                ))}
            </div>

            {/* Menu items */}
            <div className="grid grid-cols-1 gap-3">
                {filtered.length === 0 && (
                    <p className="text-center text-gray-400 py-8 text-sm">Нет блюд в этой категории</p>
                )}
                {filtered.map(item => (
                    <div key={item.id} className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4">
                        <div className="flex justify-between items-start">
                            <div className="flex-1">
                                <div className="flex items-center gap-2">
                                    <h3 className="font-bold text-slate-800">{item.name}</h3>
                                    {item.badge && (
                                        <span className="bg-red-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
                                            {item.badge}
                                        </span>
                                    )}
                                </div>
                                <p className="text-xs text-gray-500 mt-1">{item.description}</p>
                            </div>
                        </div>

                        {/* Composition toggle */}
                        {item.composition && item.composition.length > 0 && (
                            <div className="mt-2">
                                <button
                                    onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
                                    className="text-xs text-emerald-700 font-semibold hover:text-emerald-900 transition-colors"
                                >
                                    {expandedId === item.id ? '▾ Скрыть состав' : '▸ Состав блюда'}
                                </button>
                                {expandedId === item.id && (
                                    <ul className="mt-1.5 space-y-0.5">
                                        {item.composition.map((c, idx) => (
                                            <li key={idx} className="text-[11px] text-gray-500 pl-3 relative before:content-['·'] before:absolute before:left-0 before:text-gray-400">
                                                {c}
                                            </li>
                                        ))}
                                    </ul>
                                )}
                            </div>
                        )}

                        <div className="flex justify-between items-center mt-3">
                            <span className="font-extrabold text-emerald-800 text-lg">{item.price}₽</span>
                            <button
                                onClick={() => onAddToCart(item)}
                                className="bg-emerald-50 text-emerald-800 px-4 py-1.5 rounded-xl text-sm font-bold border border-emerald-200 hover:bg-emerald-100 active:scale-95 transition-all"
                            >
                                + В корзину
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default Restaurant;
export type { MenuItem };
