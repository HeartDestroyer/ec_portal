
/**
 * Типы для работы с переменными окружения
 * Содержит типы для работы с переменными окружения
 */

interface ImportMetaEnv {
    readonly BACKEND_URL: string;
    readonly FRONTEND_URL: string;
}

interface ImportMeta {
    readonly env: ImportMetaEnv;
} 