import React, { useState } from 'react';

interface GuideItem {
    id: number;
    name: string;
    description: string;
    mapUrl: string;
    category: string;
}

const guideItems: GuideItem[] = [
    // Nature & Parks
    {
        id: 1,
        category: 'nature',
        name: 'Горный Парк Рускеала',
        description: 'Мраморный каньон, жемчужина Карелии. В 30 км от Сортавала. Подземные маршруты, катера по каньону, зип-лайн.',
        mapUrl: 'https://yandex.ru/maps/-/CPEVeFOJ'
    },
    {
        id: 2,
        category: 'nature',
        name: 'Водопады Ахинкоски',
        description: 'Красивые водопады в 20 км от Сортавала. Отличное место для фото.',
        mapUrl: 'https://yandex.ru/maps/-/CPEVeK8G'
    },
    {
        id: 3,
        category: 'nature',
        name: 'Ладожские шхеры',
        description: 'Архипелаг из множества мелких скалистых островов в Ладожском озере.',
        mapUrl: 'https://yandex.ru/maps/-/CPEViFIy'
    },
    // Cafes & Restaurants
    {
        id: 4,
        category: 'cafes',
        name: 'Ресторан Gard',
        description: 'П. Кирьявалахти. Авторская кухня, вид на Ладожское озеро. Рейтинг 4.8',
        mapUrl: 'https://yandex.ru/maps/-/CPEVe0yX'
    },
    {
        id: 5,
        category: 'cafes',
        name: 'Приладожье',
        description: 'П. Рауталахти. Кафе-ресторан с карельской кухней и видом на озеро. Рейтинг 4.7',
        mapUrl: 'https://yandex.ru/maps/-/CPEVe2Ia'
    },
    {
        id: 6,
        category: 'cafes',
        name: 'Пиипун Пиха',
        description: 'г. Сортавала. Карельская и финская кухня, уютная атмосфера. Рейтинг 4.6',
        mapUrl: 'https://yandex.ru/maps/-/CDFxuRCa'
    },
    {
        id: 7,
        category: 'cafes',
        name: 'Карельская Горница',
        description: 'г. Сортавала. Традиционные калитки, уха на сливках, домашняя выпечка. Рейтинг 4.8',
        mapUrl: 'https://yandex.ru/maps/-/CDFxuS3c'
    },
    // Activities & Rent
    {
        id: 8,
        category: 'rent',
        name: 'Прогулки по Ладоге',
        description: 'Аренда катеров и прогулки по островам Ладожского озера. Незабываемые виды!',
        mapUrl: 'https://yandex.ru/maps/-/CPEViFIy'
    },
    {
        id: 9,
        category: 'rent',
        name: 'Рускеальский экспресс',
        description: 'Путешествие на старинном паровозе до парка Рускеала через живописные места.',
        mapUrl: 'https://yandex.ru/maps/-/CDFxuVRt'
    }
];

const categories = [
    { id: 'nature', label: '🌲 Природа', color: 'emerald' },
    { id: 'cafes', label: '☕ Кафе', color: 'amber' },
    { id: 'rent', label: '🚤 Активности', color: 'sky' },
];

const Guide: React.FC = () => {
    const [activeCategory, setActiveCategory] = useState('nature');
    const filtered = guideItems.filter(i => i.category === activeCategory);

    return (
        <div className="space-y-5 animate-fade-in">
            <h2 className="text-2xl font-bold px-1 text-emerald-900">Гид по Карелии</h2>

            {/* Category tabs */}
            <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
                {categories.map(cat => (
                    <button
                        key={cat.id}
                        onClick={() => setActiveCategory(cat.id)}
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

            {/* Items */}
            <div className="grid grid-cols-1 gap-3">
                {filtered.map(item => (
                    <div key={item.id} className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4">
                        <h3 className="font-bold text-slate-800 text-base">{item.name}</h3>
                        <p className="text-gray-500 text-sm mt-1 leading-relaxed">{item.description}</p>
                        <a
                            href={item.mapUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center text-emerald-700 font-bold text-sm mt-2 hover:text-emerald-900 transition-colors"
                        >
                            📍 На карте
                        </a>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default Guide;
