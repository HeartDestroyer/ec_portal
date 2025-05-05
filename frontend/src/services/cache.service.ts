/**
 * Сервис для работы с кэшем
 * Содержит методы для работы с кэшем
 */

import { apiService } from './api.service';
import { API_CONFIG } from '@/config/app.config';
import { showBackendMessage } from '@/utils/show.message';

class CacheService {
    // Сброс кэша
    async clear() {
        try {
            const response = await apiService.post(API_CONFIG.ENDPOINTS.CACHE.CLEAR);
            showBackendMessage(response, 'success');
            return response.data;
        } catch (error) {
            showBackendMessage(error, 'error');
            throw error;
        }
    }
}

export const cache = new CacheService();
