// Компонент 404
// Страница, которая отображается, если пользователь пытается получить доступ к несуществующей странице

import React from "react";
import { Result, Button } from "antd";
import { Link } from "react-router-dom";
import { APP_CONFIG } from "@/config/app.config";

const NotFound: React.FC = () => {
    return (
        <Result
            status="404"
            title={
                <span className="text-3xl font-bold">
                    404
                </span>
            }
            subTitle={
                <span className="text-xl">
                    Страница, которую вы посетили, не существует
                </span>
            }
            extra={
                <Link to={APP_CONFIG.ROUTES.PRIVATE.START}>
                    <Button 
                        size="large"
                        type="primary"
                    >
                        Вернуться на главную страницу
                    </Button>
                </Link>
            }
        />
    );
};

export default NotFound;
