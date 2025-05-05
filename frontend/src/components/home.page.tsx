/** Стартовая страница без авторизации */

import React from "react";
import { Link } from 'react-router-dom';
import { APP_CONFIG } from '../config/app.config';

const HomePage: React.FC = ({}) => {

    return (
        <div className="flex flex-col text-center justify-center h-screen mx-6">
            <h1 className="mb-4 text-4xl">Добро пожаловать на {APP_CONFIG.NAME}</h1>
            <p className="text-xl">
                <Link to={APP_CONFIG.ROUTES.PUBLIC.LOGIN}>
                    Авторизуйтесь
                </Link>, чтобы войти на портал
            </p>
        </div>
    );
};

export default HomePage;
