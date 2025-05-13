import React, { useMemo } from 'react';
import { Breadcrumb } from 'antd';
import { Link, useLocation } from 'react-router-dom';

const Breadcrumbs: React.FC = () => {
    const location = useLocation();
    const pathSnippets = location.pathname.split('/').filter(i => i);

    const breadcrumbNameMap = useMemo(() => {
        const base: Record<string, string> = {
            '/sessions': 'Управление сессиями',
            '/admin': 'Административная панель',
            '/': 'Главная',
            '/profile': 'Профиль',
            '/letter': 'Шаблоны email писем',
            '/achievements': 'Достижения пользователя',
            '/employees': 'Сотрудники компании',
            '/company-structure': 'Структура компании',
            '/education': 'Обучение руководителей',
            '/masterclass': 'Мастер классы и тренинги',
            '/lessons': 'Обучение сотрудников',
            '/checklist': 'Чек-лист новичка',
            '/candidates': 'HR-тестирование',
            '/presentation': 'Настройка презентаций',
            '/objections': 'Возражения о неоплате',
            '/reviews': 'Отзывы партнеров',
            '/calculator': 'Калькулятор ОТС',
            '/responsible': 'Справочник ответственных лиц',
            '/audio-objections': 'Справочник аудио возражений',
            '/shop': 'Онлайн магазин Эксперт Центра',
            '/settings': 'Настройки аккаунта',
        }

        const updated: Record<string, string> = { ...base };

        if (pathSnippets.length >= 2 && pathSnippets[1] === 'shop') {
            if (pathSnippets[2] === 'details' && pathSnippets[3]) {
                const item = pathSnippets[3];
                const productName = decodeURIComponent(item.split('-')[0]);
                updated[`/shop/details/${item}`] = productName;
            }
            if (pathSnippets[2] === 'category' && pathSnippets[3]) {
                const category = pathSnippets[3];
                const categoryName = decodeURIComponent(category).replace(/\+/g, ' ');
                updated[`/shop/category/${category}`] = categoryName;
            }
        }
    
        if (pathSnippets.length >= 2 && pathSnippets[1] === 'practical') {
            if (pathSnippets[2]) {
                const urlPractical = pathSnippets[2];
                const namePractical = decodeURIComponent(urlPractical).replace(/\+/g, ' ');
                updated[`/practical/${urlPractical}`] = namePractical;
            }
            if (pathSnippets[3]) {
                const urlPractical = pathSnippets[2];
                const urlTypeTest = pathSnippets[3];
                const nameTypeTest = decodeURIComponent(urlTypeTest).replace(/\+/g, ' ');
                updated[`/practical/${urlPractical}/${urlTypeTest}`] = nameTypeTest;
            }
        }

        return updated;
    }, [pathSnippets]);
    
    const breadcrumbItems = useMemo(() => {
        const items = [
            <Breadcrumb.Item key="/">
                <Link to="/">Главная</Link>
            </Breadcrumb.Item>
        ];
        items.push(
            ...pathSnippets.map((_, index) => {
                const url = `/${pathSnippets.slice(0, index + 1).join('/')}`;
                const name = breadcrumbNameMap[url];
                if (!name || url === '/') return null;
                return (
                    <Breadcrumb.Item key={url}>
                        <Link to={url}>{name}</Link>
                    </Breadcrumb.Item>
                );
            }).filter(item => item !== null)
        );
        return items;
    }, [pathSnippets, breadcrumbNameMap]);

    return (
        <Breadcrumb>
            {breadcrumbItems}
        </Breadcrumb>
    );
};
    
export default Breadcrumbs;
