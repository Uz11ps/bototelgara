import React from 'react';

export const Header: React.FC = () => {
    return (
        <header className="bg-gradient-to-r from-emerald-600 to-teal-500 text-white pt-8 pb-12 px-6 rounded-b-[2.5rem] shadow-xl relative overflow-hidden">
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
    );
};
