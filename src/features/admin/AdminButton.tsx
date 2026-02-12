import React from 'react';

// Mock Telegram WebApp
const WebApp = (window as any).Telegram?.WebApp;

export const AdminButton: React.FC = () => {
    const handleCallAdmin = () => {
        // Option 1: Send data to bot to trigger a notification to admins
        const data = { action: 'suggested_question', text: '📞 Связаться с администратором' };
        if (WebApp) {
            WebApp.sendData(JSON.stringify(data));
        } else {
            console.log('Call Admin:', data);
            alert('Сигнал администратору отправлен');
        }
    };

    return (
        <button
            onClick={handleCallAdmin}
            className="fixed top-24 right-4 z-40 bg-white/90 backdrop-blur text-red-500 p-3 rounded-full shadow-lg border border-red-100 hover:bg-red-50 active:scale-90 transition-all flex items-center justify-center group"
            title="Вызвать администратора"
        >
            <span className="text-2xl group-hover:animate-pulse">🔔</span>
        </button>
    );
};
