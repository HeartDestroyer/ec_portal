import { LoginFormData, RegisterFormData, ResetPasswordFormData, NewPasswordFormData, AuthResponse } from '../types/auth.types';
import { apiService } from './api.service';
import { API_CONFIG } from '../config/app.config';

export const login = async (data: LoginFormData): Promise<AuthResponse> => {
    const response = await apiService.post<AuthResponse>(
        API_CONFIG.ENDPOINTS.AUTH.LOGIN,
        data
    );
    return response.data;
};

export const register = async (data: RegisterFormData): Promise<AuthResponse> => {
    const response = await apiService.post<AuthResponse>(
        API_CONFIG.ENDPOINTS.AUTH.REGISTER,
        data
    );
    return response.data;
};

export const resetPassword = async (data: ResetPasswordFormData): Promise<void> => {
    await apiService.post<void>(
        API_CONFIG.ENDPOINTS.AUTH.REQUEST_PASSWORD_RESET,
        data
    );
};

export const setNewPassword = async (data: NewPasswordFormData): Promise<void> => {
    await apiService.post<void>(
        API_CONFIG.ENDPOINTS.AUTH.RESET_PASSWORD,
        data
    );
};

export const logout = (): void => {
    window.location.href = '/login';
}; 