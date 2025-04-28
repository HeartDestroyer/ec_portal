/**
 * Сервис для работы с авторизацией
 * Содержит методы для работы с авторизацией
 */

import { API_CONFIG } from '../config/app.config';
import { apiService } from './api.service';
import { LoginFormData, RegisterFormData, ResetPasswordFormData } from '@/types/auth.types';
import { showBackendMessage } from '@/utils/show.message';

class AuthService {
    // Вход в систему
    async login(credentials: LoginFormData) {
        try {
            const response = await apiService.post(API_CONFIG.ENDPOINTS.AUTH.LOGIN, credentials);
            showBackendMessage(response, 'success');
            return response.data;
        } catch (error: any) {
            showBackendMessage(error.response, 'error');
            throw error;
        }
    }

    // Регистрация пользователя
    async register(data: RegisterFormData) {
        try {
            const response = await apiService.post(API_CONFIG.ENDPOINTS.AUTH.REGISTER, data);
            showBackendMessage(response, 'success');
            return response.data;
        } catch (error: any) {
            showBackendMessage(error.response, 'error');
            throw error;
        }
    }

    // Выход из системы
    async logout() {
        try {
            const response = await apiService.post(API_CONFIG.ENDPOINTS.AUTH.LOGOUT);
            showBackendMessage(response, 'success');
        } catch (error: any) {
            showBackendMessage(error.response, 'error');
            throw error;
        }
    }

    // Запрос на получение текущего пользователя
    async getCurrentUser() {
        const response = await apiService.get(API_CONFIG.ENDPOINTS.USER.INFO);
        return response.data;
    }

    // Запрос на сброс пароля
    async requestPasswordReset(email: string) {
        const response = await apiService.post(API_CONFIG.ENDPOINTS.AUTH.REQUEST_PASSWORD_RESET, { email });
        return response.data;
    }

    // Сброс пароля
    async resetPassword(data: ResetPasswordFormData) {
        const response = await apiService.post(API_CONFIG.ENDPOINTS.AUTH.RESET_PASSWORD, data);
        return response.data;
    }

    // Подтверждение email
    async verifyEmail(token: string) {
        try {
            const response = await apiService.get(API_CONFIG.ENDPOINTS.AUTH.VERIFY_EMAIL, { params: { token } });
            showBackendMessage(response, 'success');
            return response.data;
        } catch (error: any) {
            showBackendMessage(error.response, 'error');
            throw error;
        }
    }

    // Повторная отправка email для подтверждения
    async resendVerificationEmail() {
        const response = await apiService.post(API_CONFIG.ENDPOINTS.AUTH.RESEND_VERIFICATION);
        return response.data;
    }

    // Получение CSRF токена
    async getCSRFToken() {
        const response = await apiService.get(API_CONFIG.ENDPOINTS.AUTH.CSRF);
        return response.data;
    }
}

export const authService = new AuthService();
