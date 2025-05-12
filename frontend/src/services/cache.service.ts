/**
 * Сервис для работы с кэшем
 * Содержит методы для работы с кэшем
 */

import { apiService } from './api.service';
import { API_CONFIG } from '@/config/app.config';
import { showMessage } from '@/utils/show.message';

class CacheService {
    // Сброс кэша
    async clear() {
        try {
            const response = await apiService.post(API_CONFIG.ENDPOINTS.CACHE.CLEAR);
            showMessage(response, 'success');
            return response.data;
        } catch (error) {
            showMessage(error, 'error');
            throw error;
        }
    }
}

export const cache = new CacheService();
