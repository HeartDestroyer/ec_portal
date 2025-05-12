/**
 * Копирует текст в буфер обмена
 * @param text Текст для копирования
 * @param label Метка для отображения в сообщении
 */

import { message } from 'antd';

export const copyToClipboard = async (text: string, label: string) => {
    try {
        await navigator.clipboard.writeText(text);
        message.success(`${label} скопирован`);
    } catch (err) {
        message.error(`Ошибка при копировании: ${err}`);
    }
};
