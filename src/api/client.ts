
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export interface MenuItem {
    id: number;
    name: string;
    description: string;
    price: number;
    image_url?: string;
    category: string;
    category_type?: string;
    composition?: any;
    is_available: boolean;
    admin_comment?: string;
}

export interface GuideItem {
    id: number;
    name: string;
    description: string;
    category: string;
    image_url?: string;
    map_url?: string;
}

export const apiClient = {
    getMenu: async (): Promise<MenuItem[]> => {
        const response = await axios.get(`${API_BASE_URL}/menu`);
        return response.data;
    },
    getGuide: async (): Promise<GuideItem[]> => {
        const response = await axios.get(`${API_BASE_URL}/guide`);
        return response.data;
    }
};
