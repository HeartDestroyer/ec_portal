/**
 * Типы для работы с пользователями
 * Содержит типы для работы с пользователями
 */

export interface User {
    id: string;
    login: string;
    email: string;
    name: string;
    phone: string;
    role: string;
    additional_role: string;
    is_active: boolean;
    is_verified: boolean;
    department_id: number;

    gender: string;
    company: string;
    city: string;
    user_email: string;
    telegram_id: string;
    date_employment: string;
    date_birthday: string;
    bitrix_id: number;
    created_at: string;
    last_login: string;
}

export interface LoginFormData {
    login_or_email: string;
    password: string;
}

export interface RegisterFormData {
    login: string;
    email: string;
    password: string;
    name: string;
    phone: string;
}

export interface NewPasswordFormData {
    token: string;
    new_password: string;
    confirm_password: string;
}

export interface ResetPasswordFormData {
    email: string;
}

export interface Session {
    id: string;
    device: string;
    browser: string;
    ip: string;
    last_activity: string;
    is_current: boolean;
}
