/**
 * Контекст для авторизации
 * Содержит информацию о пользователе, аутентификацию и методы для работы с ней
 */

import React, { createContext, useContext, useState, useEffect } from 'react';
import { LoginFormData, RegisterFormData, User } from '@/types/auth.types';
import { authService } from '@/services/auth.service';

interface AuthContextType {
    isAuthenticated: boolean;
    isLoading: boolean;
    user: User | null;
    login: (data: LoginFormData) => Promise<void>;
    register: (data: RegisterFormData) => Promise<void>;
    logout: () => Promise<void>;
    loadUserData: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [user, setUser] = useState<User | null>(null);

    const loadUserData = async () => {
        setIsLoading(true);
        try {
            const response = await authService.getCurrentUser();
            setUser(response as User);
            setIsAuthenticated(true);
        } catch (error) {
            setUser(null);
            setIsAuthenticated(false);
            console.error('Ошибка загрузки данных пользователя:', error);
        } finally {
            setIsLoading(false);
        }
    };

    // Загружаем данные только при первом рендере
    useEffect(() => {
        loadUserData();
    }, []);

    const handleLogin = async (data: LoginFormData) => {
        await authService.login(data);
        setIsAuthenticated(true);
        await loadUserData();
    };

    const handleRegister = async (data: RegisterFormData) => {
        await authService.register(data);
    };

    const handleLogout = async () => {
        await authService.logout();
        setIsAuthenticated(false);
        setUser(null);
    };

    return (
        <AuthContext.Provider
            value={{ isAuthenticated, isLoading, user, login: handleLogin, register: handleRegister, logout: handleLogout, loadUserData }}
        >
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth необходимо использовать внутри контекста AuthProvider');
    }
    return context;
};
