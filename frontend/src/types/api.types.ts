export interface ApiResponse<T> {
    data: T;
    status: number;
    message?: string;
}

export interface PaginatedResponse<T> {
    data: T[];
    total: number;
    page: number;
    limit: number;
}

export interface ApiError {
    message: string;
    status: number;
    code?: string;
    details?: Record<string, string[]>;
}

export interface ApiConfig {
    baseURL: string;
    timeout: number;
    headers: Record<string, string>;
}

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'; 