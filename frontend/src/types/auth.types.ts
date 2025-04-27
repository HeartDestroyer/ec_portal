export interface User {
    id: number;
    username: string;
    email: string;
    firstName: string;
    lastName: string;
    isActive: boolean;
    role: string;
    createdAt: string;
    updatedAt: string;
}

export interface LoginFormData {
    username: string;
    password: string;
    remember: boolean;
}

export interface RegisterFormData {
    username: string;
    email: string;
    password: string;
    firstName: string;
    lastName: string;
}

export interface ResetPasswordFormData {
    email: string;
}

export interface NewPasswordFormData {
    token: string;
    password: string;
}

export interface AuthResponse {
    accessToken: string;
    refreshToken?: string;
    user: User;
}

export interface ApiError {
    message: string;
    code?: string;
    status?: number;
} 