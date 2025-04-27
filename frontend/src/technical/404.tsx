import React from "react";
import { Result, Button } from "antd";
import { Link } from "react-router-dom";
import { APP_CONFIG } from "@/config/app.config";

const NotFound: React.FC = () => {
    return (
        <Result
            status="404"
            title="404"
            subTitle="Страница, которую вы посетили, не существует"
            extra={
                <Link to={APP_CONFIG.ROUTES.PUBLIC.LOGIN}>
                    <Button type="primary">
                        Вернуться на главную страницу
                    </Button>
                </Link>
            }
        />
    );
};

export default NotFound;
