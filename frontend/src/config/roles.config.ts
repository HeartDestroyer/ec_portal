/**
 * Конфигурация ролей
 * Содержит конфигурацию ролей
 */

export const ROLES = {
    SUPERADMIN: ['superadmin'],
    ADMIN: ['superadmin', 'admin'],
    LEADER: ['superadmin', 'admin', 'leader'],
    WORKERS: ['superadmin', 'admin', 'leader', 'employee'],
    ALL: ['superadmin', 'admin', 'leader', 'employee', 'guest'],
} as const;
