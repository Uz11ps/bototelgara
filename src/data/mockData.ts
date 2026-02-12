// Types matching the database models
export interface MenuItem {
    id: number;
    name: string;
    description?: string;
    price: number;
    image_url?: string;      // from DB
    imageUrl?: string;        // alias used in components
    category: string;
    category_type?: string;
    composition?: string | string[] | { name: string; quantity: string; unit: string }[];
    is_available?: boolean;
    admin_comment?: string;
}

export interface GuideItem {
    id: number;
    name: string;
    description: string;
    category: string;
    map_url?: string;
    image_url?: string;
}

// Legacy aliases used by components
export type Place = GuideItem & { title?: string; imageUrl?: string; coordinates?: { lat: number; lng: number } };

const API_BASE = '/api';

export async function fetchMenuItems(): Promise<MenuItem[]> {
    const r = await fetch(`${API_BASE}/menu`);
    const items: MenuItem[] = await r.json();
    // Normalise: map image_url -> imageUrl for components & filter available
    return items
        .filter(i => i.is_available !== false)
        .map(i => ({ ...i, imageUrl: i.image_url || undefined }));
}

export async function fetchGuideItems(): Promise<GuideItem[]> {
    const r = await fetch(`${API_BASE}/guide`);
    return r.json();
}

// Kept for backward compatibility during transition – components that
// still import these will get empty arrays until the async version is used.
export const guidePlaces: Place[] = [];
export const menuItems: MenuItem[] = [];
