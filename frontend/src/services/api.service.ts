/**
 * Сервис для работы с API
 * Конструктор создаёт экземпляр axios с настройками по умолчанию
 * Интерсепторы для обработки ошибок и обновления токенов
 * Реализованы методы для работы с API (GET, POST, PUT, DELETE, PATCH)
 */

import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { API_CONFIG, APP_CONFIG } from '@/config/app.config';

class ApiService {
    private instance: AxiosInstance;

    constructor() {
        this.instance = axios.create({
            baseURL: API_CONFIG.BASE_URL,
            headers: {
                'Content-Type': 'application/json',
            },
            withCredentials: true
        });

        /** refreshInProgress для того чтобы не было ошибки при одновременном обновлении токенов, защита от двойного запроса на обновление токенов */
        let refreshInProgress = null as any;

        this.instance.interceptors.response.use(
            (response) => response,
            async (error: AxiosError) => {
                const originalRequest = error.config as any;

                const isAuthRequest =
                    originalRequest.url?.includes(API_CONFIG.ENDPOINTS.AUTH.LOGIN) ||
                    originalRequest.url?.includes(API_CONFIG.ENDPOINTS.AUTH.REFRESH);

                if (error.response?.status === 401 && !originalRequest._retry && !isAuthRequest) {
                    originalRequest._retry = true;
                    try {
                        if (!refreshInProgress) {
                            refreshInProgress = await this.instance.post(API_CONFIG.ENDPOINTS.AUTH.REFRESH);
                        }
                        await refreshInProgress;
                        return this.instance(originalRequest);
                    } catch (refreshError) {
                        if (window.location.pathname !== APP_CONFIG.ROUTES.PUBLIC.LOGIN) {
                            window.location.href = APP_CONFIG.ROUTES.PUBLIC.LOGIN;
                        }
                    } finally {
                        refreshInProgress = null;
                    }
                }
                return Promise.reject(error);
            }
        );
    }
                
    // Методы для работы с API
    public async get<T>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
        return this.instance.get<T>(url, config);
    }

    public async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
        return this.instance.post<T>(url, data, config);
    }

    public async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
        return this.instance.put<T>(url, data, config);
    }

    public async delete<T>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
        return this.instance.delete<T>(url, config);
    }

    public async patch<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
        return this.instance.patch<T>(url, data, config);
    }
}

export const apiService = new ApiService();

export const api = axios.create({
    baseURL: API_CONFIG.BASE_URL,
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json',
    },
}); 
