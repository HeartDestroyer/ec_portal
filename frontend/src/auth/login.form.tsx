/** Форма авторизации */

import React, { useState } from "react";
import { Form, Input, Button } from "antd";
import { Link, useNavigate } from "react-router-dom";
import { LockOutlined, UserOutlined } from '@ant-design/icons';
import { useAuth } from "@/context/auth.context";
import { LoginFormData } from "@/types/auth.types";
import { APP_CONFIG, VALIDATION_CONFIG } from "@/config/app.config";

const LoginForm: React.FC = () => {
    const navigate = useNavigate();
    const { login } = useAuth();
    const [form] = Form.useForm<LoginFormData>();
    const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

    const onFinish = async (values: LoginFormData) => {
        try {
            setIsSubmitting(true);
            await login(values);
            form.resetFields();
            navigate(APP_CONFIG.ROUTES.PRIVATE.START);
        } catch (error: any) {
            console.log("Ошибка авторизации", error);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <main className="min-h-screen flex flex-col justify-center items-center">
            <Form<LoginFormData>
                form={form}
                name="loginForm"
                layout="vertical"
                initialValues={{ remember: true }}
                className="w-full !px-3 max-w-md"
                onFinish={onFinish}
                validateTrigger={['onChange', 'onBlur']}
                autoComplete="off"
            >
                <div className="mb-8 text-2xl sm:text-3xl font-bold text-center">{APP_CONFIG.NAME}</div>

                <Form.Item<LoginFormData>
                    name="login_or_email"
                    rules={[
                        { required: true, message: 'Введите корректный логин или почту' },
                        { min: VALIDATION_CONFIG.USERNAME.MIN_LENGTH, message: `Минимальная длина ${VALIDATION_CONFIG.USERNAME.MIN_LENGTH} символов` },
                        { max: VALIDATION_CONFIG.USERNAME.MAX_LENGTH, message: `Максимальная длина ${VALIDATION_CONFIG.USERNAME.MAX_LENGTH} символов` },
                    ]}
                >
                    <Input 
                        prefix={<UserOutlined />} 
                        placeholder="Логин или почта"
                        size="large"
                    />
                </Form.Item>

                <Form.Item<LoginFormData>
                    name="password"
                    rules={[
                        { required: true, message: 'Введите корректный пароль' },
                        { min: VALIDATION_CONFIG.PASSWORD.MIN_LENGTH, message: `Минимальная длина ${VALIDATION_CONFIG.PASSWORD.MIN_LENGTH} символов` },
                        { max: VALIDATION_CONFIG.PASSWORD.MAX_LENGTH, message: `Максимальная длина ${VALIDATION_CONFIG.PASSWORD.MAX_LENGTH} символов` },
                        { pattern: VALIDATION_CONFIG.PASSWORD.PATTERN, message: 'Пароль должен содержать заглавные и строчные буквы, цифры и специальные символы $!%*?&' }
                    ]}
                >
                    <Input.Password 
                        prefix={<LockOutlined />} 
                        placeholder="Пароль"
                        size="large"
                    />
                </Form.Item>

                <div className="flex justify-between items-center mb-5 text-base">
                    <Link to={APP_CONFIG.ROUTES.PUBLIC.RESET_PASSWORD}>
                        Забыли пароль?
                    </Link>
                    <Link to={APP_CONFIG.ROUTES.PUBLIC.REGISTER}>
                        Зарегистрироваться
                    </Link>
                </div>

                <Form.Item>
                    <Button
                        type="primary"
                        htmlType="submit"
                        block
                        size="large"
                        loading={isSubmitting}
                        disabled={isSubmitting}
                    >
                        Войти на {APP_CONFIG.NAME}
                    </Button>
                </Form.Item>
            </Form>
        </main>
    );
};

export default LoginForm; 