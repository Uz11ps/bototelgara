import React, { useState } from 'react';
import { MenuItem } from './Restaurant';

interface CartItem extends MenuItem {
    quantity: number;
}

interface CartProps {
    items: CartItem[];
    onUpdateQuantity: (id: number, delta: number) => void;
    onClose: () => void;
    onOrder: (room: string, comment: string) => void;
}

const Cart: React.FC<CartProps> = ({ items, onUpdateQuantity, onClose, onOrder }) => {
    const [room, setRoom] = useState('');
    const [comment, setComment] = useState('');
    const total = items.reduce((sum, item) => sum + item.price * item.quantity, 0);

    if (items.length === 0) {
        return (
            <div className="bg-white rounded-2xl p-6 text-center space-y-4 shadow-xl">
                <span className="text-5xl">🛒</span>
                <h2 className="text-xl font-bold text-slate-800">Корзина пуста</h2>
                <p className="text-gray-500">Добавьте что-нибудь вкусное!</p>
                <button
                    onClick={onClose}
                    className="w-full bg-gray-100 text-gray-800 py-3 rounded-xl font-bold active:scale-[0.98] transition-transform"
                >
                    Вернуться к меню
                </button>
            </div>
        );
    }

    return (
        <div className="bg-white rounded-2xl p-4 shadow-xl border border-gray-100">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold">Ваш заказ</h2>
                <button onClick={onClose} className="text-gray-400 text-2xl">×</button>
            </div>

            <div className="space-y-3 max-h-60 overflow-y-auto mb-4">
                {items.map((item) => (
                    <div key={item.id} className="flex justify-between items-center border-b border-gray-50 pb-3">
                        <div className="flex-1">
                            <h4 className="font-bold text-sm">{item.name}</h4>
                            <p className="text-xs text-gray-500">{item.price * item.quantity}₽</p>
                        </div>
                        <div className="flex items-center space-x-3 bg-gray-50 p-1 rounded-lg">
                            <button
                                onClick={() => onUpdateQuantity(item.id, -1)}
                                className="w-8 h-8 flex items-center justify-center bg-white rounded shadow-sm text-lg font-bold"
                            >
                                -
                            </button>
                            <span className="font-bold w-4 text-center">{item.quantity}</span>
                            <button
                                onClick={() => onUpdateQuantity(item.id, 1)}
                                className="w-8 h-8 flex items-center justify-center bg-white rounded shadow-sm text-lg font-bold"
                            >
                                +
                            </button>
                        </div>
                    </div>
                ))}
            </div>

            {/* Room number & comment inputs */}
            <div className="space-y-3 mb-4">
                <div>
                    <label className="text-xs font-semibold text-gray-600 mb-1 block">Номер комнаты *</label>
                    <input
                        type="text"
                        value={room}
                        onChange={e => setRoom(e.target.value)}
                        placeholder="Например: 12"
                        className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 bg-gray-50"
                    />
                </div>
                <div>
                    <label className="text-xs font-semibold text-gray-600 mb-1 block">Комментарий</label>
                    <textarea
                        value={comment}
                        onChange={e => setComment(e.target.value)}
                        placeholder="Пожелания к заказу..."
                        rows={2}
                        className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 bg-gray-50 resize-none"
                    />
                </div>
            </div>

            <div className="space-y-3 pt-3 border-t border-gray-100">
                <div className="flex justify-between text-lg font-bold">
                    <span>Итого:</span>
                    <span className="text-green-800">{total}₽</span>
                </div>
                <button
                    onClick={() => onOrder(room, comment)}
                    disabled={!room.trim()}
                    className={`w-full py-4 rounded-xl font-bold text-lg shadow-lg active:scale-[0.98] transition-all ${
                        room.trim()
                            ? 'premium-gradient text-white shadow-emerald-900/20'
                            : 'bg-gray-200 text-gray-400 cursor-not-allowed shadow-none'
                    }`}
                >
                    {room.trim() ? 'Оформить заказ' : 'Укажите номер комнаты'}
                </button>
            </div>
        </div>
    );
};

export default Cart;
export type { CartItem };
