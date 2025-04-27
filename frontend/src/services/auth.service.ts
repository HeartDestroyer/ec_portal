import { API_CONFIG } from '../config/app.config';
import { api } from './api.service';

interface LoginCredentials {
    email: string;
    password: string;
}

interface RegisterData {
    email: string;
    password: string;
    name: string;
}

class AuthService {
    async login(credentials: LoginCredentials) {
        const response = await api.post('/auth/login', credentials);
        return response.data;
    }

    async register(data: RegisterData) {
        const response = await api.post('/auth/register', data);
        return response.data;
    }

    async logout() {
        await api.post('/auth/logout');
    }

    async getCurrentUser() {
        const response = await api.get('/auth/me');
        return response.data;
    }
}

export const authService = new AuthService(); 