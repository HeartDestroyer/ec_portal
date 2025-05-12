/**
 * Универсальная функция для вывода сообщений от бэка.
 * @param response - объект ответа или ошибки от axios
 * @param type - 'success' | 'error' | 'info' | 'warning'
 * @param fallback - сообщение по умолчанию, если с бэка ничего не пришло
 */

import { message } from "antd";

export function showMessage(
    response: any,
    type: 'success' | 'error' | 'info' | 'warning' = 'success',
    fallback?: string
) {
    let msg = 
        response?.data?.message  ||
        (Array.isArray(response?.data) && response.data[0]?.message)  ||
        (Array.isArray(response) && response[0]?.message);

    if (!msg && fallback) msg = fallback;
    if (msg) message[type](msg);
}
