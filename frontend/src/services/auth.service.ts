/**
 * Сервис для работы с авторизацией
 * Содержит методы для работы с авторизацией
 */

import { API_CONFIG } from '../config/app.config';
import { apiService } from './api.service';
import { LoginFormData, RegisterFormData, NewPasswordFormData } from '@/types/auth.types';
import { showMessage } from '@/utils/show.message';

/** Сервис для работы с авторизацией */
class AuthService {

    /** Вход в систему */
    async login(credentials: LoginFormData) {
        try {
            const response = await apiService.post(API_CONFIG.ENDPOINTS.AUTH.LOGIN, credentials);
            showMessage(response, 'success');
            return response.data;
        } catch (error: any) {
            showMessage(error.response, 'error');
            throw error;
        }
    }

    /** Регистрация пользователя */
    async register(data: RegisterFormData) {
        try {
            const response = await apiService.post(API_CONFIG.ENDPOINTS.AUTH.REGISTER, data);
            showMessage(response, 'success');
            return response.data;
        } catch (error: any) {
            showMessage(error.response, 'error');
            throw error;
        }
    }

    /** Выход из системы */
    async logout() {
        try {
            const response = await apiService.post(API_CONFIG.ENDPOINTS.AUTH.LOGOUT);
            showMessage(response, 'success');
        } catch (error: any) {
            showMessage(error.response, 'error');
            throw error;
        }
    }

    /** Получение данных текущего пользователя */
    async getCurrentUser() {
        const response = await apiService.get(API_CONFIG.ENDPOINTS.USER.INFO);
        return response.data;
    }

    /** Запрос на сброс пароля */
    async requestPasswordReset(email: string) {
        try {
            const response = await apiService.post(API_CONFIG.ENDPOINTS.AUTH.REQUEST_PASSWORD_RESET, { email });
            showMessage(response, 'success');
            return response.data;
        } catch (error: any) {
            showMessage(error.response, 'error');
            throw error;
        }
    }

    /** Установка нового пароля - Сброс пароля */
    async setNewPassword(data: NewPasswordFormData) {
        try {
            const response = await apiService.post(API_CONFIG.ENDPOINTS.AUTH.RESET_PASSWORD, data);
            showMessage(response, 'success');
            return response.data;
        } catch (error: any) {
            showMessage(error.response, 'error');
            throw error;
        }
    }

    /** Подтверждение email */
    async verifyEmail(token: string) {
        try {
            const response = await apiService.get(API_CONFIG.ENDPOINTS.AUTH.VERIFY_EMAIL, { params: { token } });
            showMessage(response, 'success');
            return response.data;
        } catch (error: any) {
            showMessage(error.response, 'error');
            throw error;
        }
    }

    /** Повторная отправка email для подтверждения */
    async resendVerificationEmail() {
        const response = await apiService.post(API_CONFIG.ENDPOINTS.AUTH.RESEND_VERIFICATION);
        return response.data;
    }

    /** Получение CSRF токена */
    async getCSRFToken() {
        const response = await apiService.get(API_CONFIG.ENDPOINTS.AUTH.CSRF);
        return response.data;
    }

    /** Получение активных сессий пользователя */
    async getActiveSessions() {
        try {
            const response = await apiService.get(API_CONFIG.ENDPOINTS.AUTH.SESSIONS);
            return response.data;
        } catch (error: any) {
            showMessage(error.response, 'error');
            throw error;
        }
    }

    /** Завершение конкретной сессии */
    async terminateSession(sessionId: string) {
        try {
            const response = await apiService.delete(`${API_CONFIG.ENDPOINTS.AUTH.SESSIONS}/${sessionId}`);
            showMessage(response, 'success');
            return response.data;
        } catch (error: any) {
            showMessage(error.response, 'error');
            throw error;
        }
    }

    /** Завершение всех сессий кроме текущей */
    async terminateOtherSessions() {
        try {
            const response = await apiService.delete(API_CONFIG.ENDPOINTS.AUTH.SESSIONS);
            showMessage(response, 'success');
            return response.data;
        } catch (error: any) {
            showMessage(error.response, 'error');
            throw error;
        }
    }
}

export const authService = new AuthService();
