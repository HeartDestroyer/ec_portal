import React, { useState } from "react";
import { Form, Input, Button } from "antd";
import { Link, useNavigate } from "react-router-dom";
import { MailOutlined } from '@ant-design/icons';
import { authService } from "@/services/auth.service";
import { ResetPasswordFormData } from "@/types/auth.types";
import { APP_CONFIG } from "@/config/app.config";

const ResetPassword: React.FC = () => {
    const navigate = useNavigate();
    const [form] = Form.useForm<ResetPasswordFormData>();
    const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

    const onFinish = async (values: ResetPasswordFormData) => {
        try {
            setIsSubmitting(true);
            await authService.requestPasswordReset(values.email);
            navigate(APP_CONFIG.ROUTES.PUBLIC.LOGIN);
        } catch (error) {
            console.error("Ошибка восстановления пароля:", error);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="flex justify-center items-center h-screen px-4">
            <Form<ResetPasswordFormData>
                form={form}
                name="password-recovery"
                className="flex flex-col w-full !px-3 max-w-md"
                onFinish={onFinish}
            >
                <div className="mb-8 text-2xl sm:text-3xl font-bold text-center">Восстановление пароля на {APP_CONFIG.NAME}е</div>

                <Form.Item<ResetPasswordFormData>
                    name="email"
                    rules={[
                        { required: true, message: 'Введите корректную почту' },
                        { type: 'email', message: 'Введите корректную почту' }
                    ]}
                >
                    <Input 
                        prefix={<MailOutlined />} 
                        size="large" 
                        placeholder="Почта" 
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
                        type="primary"
                        htmlType="submit"
                        block
                        size="large"
                        loading={isSubmitting}
                        disabled={isSubmitting}
                    >
                        Отправить инструкции на почту
                    </Button>
                </Form.Item>
            </Form>
        </div>
    );
};

export default ResetPassword; 