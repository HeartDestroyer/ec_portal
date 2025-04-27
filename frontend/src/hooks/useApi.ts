import { useState, useCallback } from 'react';
import { apiService } from '@/services/api.service';
import { ApiResponse, ApiError } from '@/types';

interface UseApiOptions<T> {
    onSuccess?: (data: T) => void;
    onError?: (error: ApiError) => void;
}

export const useApi = <T,>(endpoint: string, options: UseApiOptions<T> = {}) => {
    const [data, setData] = useState<T | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<ApiError | null>(null);

    const execute = useCallback(async (params?: Record<string, any>) => {
        setLoading(true);
        setError(null);

        try {
            const response = await apiService.get<ApiResponse<T>>(endpoint, params);
            setData(response.data);
            options.onSuccess?.(response.data);
            return response.data;
        } catch (err) {
            const apiError = err as ApiError;
            setError(apiError);
            options.onError?.(apiError);
            throw apiError;
        } finally {
            setLoading(false);
        }
    }, [endpoint, options]);

    return { data, loading, error, execute };
}; 