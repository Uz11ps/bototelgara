import React, { useState } from 'react';
import { MenuItem } from '../../data/mockData';

// Telegram WebApp
const WebApp = (window as any).Telegram?.WebApp;

interface CartProps {
    cart: { [itemId: number]: number };
    items: MenuItem[];
    onUpdateCart: (itemId: number, newQty: number) => void;
    onClose: () => void;
}

export const Cart: React.FC<CartProps> = ({ cart, items, onUpdateCart, onClose }) => {
    const [isOrdering, setIsOrdering] = useState(false);

    const cartItems = Object.entries(cart).map(([id, qty]) => {
        const item = items.find((i) => i.id === Number(id));
        return item ? { ...item, qty } : null;
    }).filter((item): item is MenuItem & { qty: number } => item !== null);

    const total = cartItems.reduce((sum, item) => sum + item.price * item.qty, 0);

    const handleOrder = () => {
        setIsOrdering(true);
        const orderData = {
            action: 'web_app_order',
            cart: cartItems.map(item => ({
                id: item.id,
                name: item.name,
                quantity: item.qty,
                price: item.price
            })),
            total: total
        };

        // Send data to bot
        if (WebApp) {
            WebApp.sendData(JSON.stringify(orderData));
        } else {
            console.log('WebApp.sendData:', orderData);
            alert('Заказ отправлен (в режиме разработки)');
        }
    };

    if (cartItems.length === 0) {
        return (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-fade-in">
                <div className="bg-white rounded-[2rem] p-8 w-full max-w-sm text-center shadow-2xl">
                    <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4 text-3xl">🛒</div>
                    <h3 className="text-xl font-bold text-slate-800 mb-2">Корзина пуста</h3>
                    <p className="text-slate-500 mb-6">Добавьте вкусные блюда из меню</p>
                    <button
                        onClick={onClose}
                        className="w-full py-3 bg-emerald-100 text-emerald-800 rounded-xl font-bold hover:bg-emerald-200 transition-colors"
                    >
                        Вернуться в меню
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="fixed inset-0 z-50 flex flex-col bg-white animate-slide-up">
            <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-white/80 backdrop-blur-md sticky top-0 z-10">
                <h2 className="text-xl font-bold text-slate-800">Ваш заказ</h2>
                <button
                    onClick={onClose}
                    className="w-8 h-8 flex items-center justify-center rounded-full bg-slate-100 text-slate-500 hover:bg-slate-200"
                >
                    ✕
                </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4 pb-32">
                {cartItems.map((item) => (
                    <div key={item.id} className="flex gap-4 p-3 bg-white border border-slate-100 rounded-2xl shadow-sm">
                        {(item.imageUrl || item.image_url) && (
                            <img src={item.imageUrl || item.image_url} alt={item.name} className="w-20 h-20 rounded-xl object-cover" />
                        )}
                        <div className="flex-1 flex flex-col justify-between">
                            <div>
                                <h4 className="font-bold text-slate-800 line-clamp-1">{item.name}</h4>
                                <p className="text-emerald-600 font-bold">{item.price} ₽</p>
                            </div>

                            <div className="flex items-center gap-3 mt-2">
                                <button
                                    onClick={() => onUpdateCart(item.id, item.qty - 1)}
                                    className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-600 font-bold hover:bg-slate-200"
                                >
                                    -
                                </button>
                                <span className="font-bold w-4 text-center">{item.qty}</span>
                                <button
                                    onClick={() => onUpdateCart(item.id, item.qty + 1)}
                                    className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-700 font-bold hover:bg-emerald-200"
                                >
                                    +
                                </button>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            <div className="p-4 border-t border-slate-100 bg-white shadow-up-lg safe-area-bottom">
                <div className="flex justify-between items-center mb-4">
                    <span className="text-slate-500 font-medium">Итого:</span>
                    <span className="text-2xl font-bold text-emerald-800">{total} ₽</span>
                </div>
                <button
                    onClick={handleOrder}
                    disabled={isOrdering}
                    className="w-full py-4 bg-gradient-to-r from-emerald-600 to-teal-500 text-white rounded-2xl font-bold shadow-lg shadow-emerald-500/30 active:scale-[0.98] transition-all disabled:opacity-70 disabled:cursor-not-allowed flex justify-center items-center"
                >
                    {isOrdering ? (
                        <>
                            <span className="animate-spin mr-2">⏳</span> Оформляем...
                        </>
                    ) : (
                        'Оформить заказ'
                    )}
                </button>
            </div>
        </div>
    );
};
