import React, { useState } from "react";
import { Form, Input, Button } from "antd";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { LockOutlined } from '@ant-design/icons';
import { NewPasswordFormData } from "@/types/auth.types";
import { authService } from "@/services/auth.service";
import { APP_CONFIG, VALIDATION_CONFIG } from "@/config/app.config";

const ResetPassword: React.FC = () => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const [form] = Form.useForm<NewPasswordFormData>();
    const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

    const token = searchParams.get('token');
    if (!token) {
        navigate(APP_CONFIG.ROUTES.PUBLIC.LOGIN);
        return null;
    }

    const onFinish = async (values: NewPasswordFormData) => {
        try {
            setIsSubmitting(true);
            await authService.setNewPassword({ ...values, token });
            navigate(APP_CONFIG.ROUTES.PUBLIC.LOGIN);
        } catch (error) {
            console.error("Ошибка сброса пароля:", error);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="flex justify-center items-center h-screen px-4">
            <Form<NewPasswordFormData>
                form={form}
                name="password"
                className="w-full !px-3 max-w-md"
                onFinish={onFinish}
            >
                <div className="mb-8 text-2xl sm:text-3xl font-bold text-center">Сброс пароля на {APP_CONFIG.NAME}е</div>

                <Form.Item<NewPasswordFormData>
                    name="new_password"
                    rules={[
                        { required: true, message: 'Введите новый пароль' },
                        { min: VALIDATION_CONFIG.PASSWORD.MIN_LENGTH, message: `Минимальная длина ${VALIDATION_CONFIG.PASSWORD.MIN_LENGTH} символов` },
                        { max: VALIDATION_CONFIG.PASSWORD.MAX_LENGTH, message: `Максимальная длина ${VALIDATION_CONFIG.PASSWORD.MAX_LENGTH} символов` },
                        { pattern: VALIDATION_CONFIG.PASSWORD.PATTERN, message: 'Пароль должен содержать заглавные и строчные буквы, цифры и специальные символы $!%*?&' }
                    ]}
                >
                    <Input.Password 
                        size="large" 
                        prefix={<LockOutlined />} 
                        placeholder="Новый пароль" 
                    />
                </Form.Item>

                <Form.Item<NewPasswordFormData>
                    name="confirm_password"
                    dependencies={['new_password']}
                    rules={[
                        { required: true, message: 'Повторите новый пароль' },
                        ({ getFieldValue }) => ({
                            validator(_, value) {
                                if (!value || getFieldValue('new_password') === value) {
                                    return Promise.resolve();
                                }
                                return Promise.reject(new Error('Пароли не совпадают'));
                            },
                        }),
                    ]}
                >
                    <Input.Password 
                        size="large" 
                        prefix={<LockOutlined />} 
                        placeholder="Подтвердите пароль" 
                    />
                </Form.Item>

                <div className="flex justify-between items-center mb-5 text-base">
                    <span>Вспомнили пароль?</span>
                    <Link to={APP_CONFIG.ROUTES.PUBLIC.LOGIN}>
                        Вернуться к входу
                    </Link>
                </div>

                <Form.Item>
                    <Button 
                        size="large" 
                        block 
                        type="primary" 
                        htmlType="submit"
                        loading={isSubmitting}
                        disabled={isSubmitting}
                    >
                        Установить новый пароль
                    </Button>
                </Form.Item>
            </Form>
        </div>
    );
};

export default ResetPassword; 