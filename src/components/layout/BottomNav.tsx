import React from 'react';

interface BottomNavProps {
    activeTab: string;
    setActiveTab: (tab: string) => void;
}

export const BottomNav: React.FC<BottomNavProps> = ({ activeTab, setActiveTab }) => {
    return (
        <nav className="fixed bottom-6 left-4 right-4 bg-white/80 backdrop-blur-md rounded-[2rem] p-2 flex justify-between shadow-2xl z-50 ring-1 ring-black/5">
            {[
                { id: 'home', label: 'Отель', icon: '🏨' },
                { id: 'guide', label: 'Гид', icon: '🗺️' },
                { id: 'menu', label: 'Меню', icon: '🍽' },
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
    );
};
