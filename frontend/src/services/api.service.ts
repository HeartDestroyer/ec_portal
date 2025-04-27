import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { API_CONFIG } from '@/config/app.config';

interface CustomAxiosRequestConfig extends AxiosRequestConfig {
    _retry?: boolean;
}

class ApiService {
    private instance: AxiosInstance;
    private isRefreshing: boolean = false;
    private refreshSubscribers: ((token: string) => void)[] = [];

    constructor() {
        this.instance = axios.create({
            baseURL: API_CONFIG.BASE_URL,
            headers: {
                'Content-Type': 'application/json',
            },
            withCredentials: true // Включаем поддержку куки
        });

        this.instance.interceptors.request.use(
            (config) => {
                const token = localStorage.getItem(API_CONFIG.TOKEN.ACCESS);
                if (token) {
                    config.headers.Authorization = `Bearer ${token}`;
                }
                return config;
            },
            (error) => Promise.reject(error)
        );

        this.instance.interceptors.response.use(
            (response) => response,
            async (error: AxiosError) => {
                const originalRequest = error.config as CustomAxiosRequestConfig;
                
                if (error.response?.status === 401 && !originalRequest?._retry) {
                    if (this.isRefreshing) {
                        return new Promise((resolve) => {
                            this.refreshSubscribers.push((token: string) => {
                                if (originalRequest?.headers) {
                                    originalRequest.headers.Authorization = `Bearer ${token}`;
                                }
                                resolve(this.instance(originalRequest!));
                            });
                        });
                    }

                    originalRequest!._retry = true;
                    this.isRefreshing = true;

                    try {
                        const response = await this.refreshToken();
                        const { accessToken } = response.data;
                        
                        localStorage.setItem(API_CONFIG.TOKEN.ACCESS, accessToken);
                        
                        if (originalRequest?.headers) {
                            originalRequest.headers.Authorization = `Bearer ${accessToken}`;
                        }
                        
                        this.refreshSubscribers.forEach((callback) => callback(accessToken));
                        this.refreshSubscribers = [];
                        
                        return this.instance(originalRequest!);
                    } catch (refreshError) {
                        localStorage.removeItem(API_CONFIG.TOKEN.ACCESS);
                        localStorage.removeItem(API_CONFIG.TOKEN.REFRESH);
                        window.location.href = '/login';
                        return Promise.reject(refreshError);
                    } finally {
                        this.isRefreshing = false;
                    }
                }

                return Promise.reject(error);
            }
        );
    }

    private async refreshToken() {
        return this.instance.post(API_CONFIG.ENDPOINTS.AUTH.REFRESH);
    }

    public async get<T>(url: string, config?: CustomAxiosRequestConfig): Promise<AxiosResponse<T>> {
        return this.instance.get<T>(url, config);
    }

    public async post<T>(url: string, data?: any, config?: CustomAxiosRequestConfig): Promise<AxiosResponse<T>> {
        return this.instance.post<T>(url, data, config);
    }

    public async put<T>(url: string, data?: any, config?: CustomAxiosRequestConfig): Promise<AxiosResponse<T>> {
        return this.instance.put<T>(url, data, config);
    }

    public async delete<T>(url: string, config?: CustomAxiosRequestConfig): Promise<AxiosResponse<T>> {
        return this.instance.delete<T>(url, config);
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