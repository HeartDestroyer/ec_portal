/**
 * Сервис для работы с сессиями
 * Содержит методы для работы с сессиями
 */

import { API_CONFIG } from '../config/app.config';
import { apiService } from './api.service';
import { showMessage } from '@/utils/show.message';
import type { SessionsPage, SessionFilter } from '@/types/session.types';

class SessionService {

    /** Получение сессий всех пользователей для администратора */
    async getSessions(filter: SessionFilter): Promise<SessionsPage> {
        try {
            const response = await apiService.get(API_CONFIG.ENDPOINTS.SESSIONS.ADMIN_SESSIONS, { params: filter });
            return response.data as SessionsPage;
        } catch (error: any) {
            showMessage(error.response, 'error');
            throw error;
        }
    }

    /** Получение активных сессий пользователя */
    async getActiveSessions(filter: SessionFilter): Promise<SessionsPage> {
        try {
            const response = await apiService.get(API_CONFIG.ENDPOINTS.SESSIONS.SESSIONS, { params: filter });
            return response.data as SessionsPage;
        } catch (error: any) {
            showMessage(error.response, 'error');
            throw error;
        }
    }

    /** Завершение конкретной сессии */
    async terminateSession(sessionId: string): Promise<void> {
        try {
            const response = await apiService.delete(`${API_CONFIG.ENDPOINTS.SESSIONS.SESSIONS}/${sessionId}`);
            showMessage(response, 'success');
            return response.data as void;
        } catch (error: any) {
            showMessage(error.response, 'error');
            throw error;
        }
    }

    /** Завершение всех сессий кроме текущей */
    async terminateOtherSessions(): Promise<void> {
        try {
            const response = await apiService.delete(API_CONFIG.ENDPOINTS.SESSIONS.SESSIONS);
            showMessage(response, 'success');
            return response.data as void;
        } catch (error: any) {
            showMessage(error.response, 'error');
            throw error;
        }
    }

}

export const sessionService = new SessionService();
