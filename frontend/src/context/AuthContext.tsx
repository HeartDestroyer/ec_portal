import React, { createContext, useContext, useState, useEffect } from 'react';
import { login, logout, register } from '@/services/authService';
import { LoginFormData, RegisterFormData, AuthResponse, User } from '@/types/auth.types';
import { apiService } from '@/services/api.service';
import { API_CONFIG } from '@/config/app.config';

interface AuthContextType {
    isAuthenticated: boolean;
    isLoading: boolean;
    user: User | null;
    login: (data: LoginFormData) => Promise<void>;
    register: (data: RegisterFormData) => Promise<void>;
    logout: () => void;
    loadUserData: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [user, setUser] = useState<User | null>(null);

    const loadUserData = async () => {
        try {
            const response = await apiService.get<User>('/api/v1/user/profile');
            setUser(response.data);
        } catch (error) {
            console.error('Ошибка загрузки данных пользователя:', error);
        }
    };

    useEffect(() => {
        const checkAuth = async () => {
            try {
                await apiService.get('/api/v1/auth/verify');
                setIsAuthenticated(true);
                await loadUserData();
            } catch (error) {
                setIsAuthenticated(false);
                setUser(null);
            } finally {
                setIsLoading(false);
            }
        };

        checkAuth();
    }, []);

    const handleLogin = async (data: LoginFormData) => {
        await login(data);
        setIsAuthenticated(true);
        await loadUserData();
    };

    const handleRegister = async (data: RegisterFormData) => {
        await register(data);
        setIsAuthenticated(true);
        await loadUserData();
    };

    const handleLogout = () => {
        logout();
        setIsAuthenticated(false);
        setUser(null);
    };

    return (
        <AuthContext.Provider
            value={{
                isAuthenticated,
                isLoading,
                user,
                login: handleLogin,
                register: handleRegister,
                logout: handleLogout,
                loadUserData,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}; 