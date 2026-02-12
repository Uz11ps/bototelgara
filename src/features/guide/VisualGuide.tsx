import React, { useState, useEffect } from 'react';
import { fetchGuideItems, GuideItem } from '../../data/mockData';

export const VisualGuide: React.FC = () => {
    const [places, setPlaces] = useState<GuideItem[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchGuideItems()
            .then(data => { setPlaces(data); setLoading(false); })
            .catch(() => setLoading(false));
    }, []);

    if (loading) {
        return (
            <div className="flex justify-center items-center py-20 animate-fade-in">
                <div className="w-8 h-8 border-4 border-emerald-200 border-t-emerald-600 rounded-full animate-spin"></div>
            </div>
        );
    }

    return (
        <div className="space-y-6 animate-fade-in pb-24">
            <div className="glass-card p-6 shadow-sm">
                <h2 className="text-2xl font-bold mb-3 text-emerald-900">Гид по местам</h2>
                <p className="text-slate-600 leading-relaxed">
                    Откройте для себя красоту Карелии.
                </p>
            </div>

            <div className="grid gap-6">
                {places.length === 0 ? (
                    <div className="text-center py-10 text-slate-400">Места не найдены</div>
                ) : places.map((place) => (
                    <div key={place.id} className="glass-card overflow-hidden shadow-md hover:shadow-lg transition-shadow">
                        {place.image_url && (
                            <div className="h-48 relative">
                                <img
                                    src={place.image_url}
                                    alt={place.name}
                                    className="w-full h-full object-cover"
                                />
                                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-4">
                                    <h3 className="text-xl font-bold text-white">{place.name}</h3>
                                </div>
                            </div>
                        )}
                        {!place.image_url && (
                            <div className="p-4 border-b border-slate-100">
                                <h3 className="text-xl font-bold text-emerald-900">{place.name}</h3>
                            </div>
                        )}
                        <div className="p-4">
                            <p className="text-slate-700">{place.description}</p>
                            {place.map_url && (
                                <a
                                    href={place.map_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-block mt-3 text-emerald-600 font-semibold hover:text-emerald-700"
                                >
                                    📍 Открыть на карте
                                </a>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};
