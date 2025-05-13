import React, { useState } from "react";
import { Form, Input, Button } from "antd";
import { Link, useNavigate } from "react-router-dom";
import { UserOutlined, MailOutlined, LockOutlined, PhoneOutlined } from '@ant-design/icons';
import { RegisterFormData } from "@/types/auth.types";
import { useAuth } from "@/context/auth.context";
import { APP_CONFIG, VALIDATION_CONFIG } from "@/config/app.config";

const RegisterForm: React.FC = () => {
    const navigate = useNavigate();
    const { register } = useAuth();
    const [form] = Form.useForm<RegisterFormData>();
    const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

    const onFinish = async (values: RegisterFormData) => {
        try {
            setIsSubmitting(true);
            await register(values);
            navigate(APP_CONFIG.ROUTES.PUBLIC.LOGIN);
        } catch (error) {
            console.log("Ошибка регистрации", error);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <main className="min-h-screen flex flex-col justify-center items-center">
            <Form<RegisterFormData>
                form={form}
                name="registerForm"
                layout="vertical"
                initialValues={{ remember: true }}
                className="w-full !px-3 max-w-md"
                onFinish={onFinish}
                validateTrigger={['onChange', 'onBlur']}
                autoComplete="off"
            >
                <div className="mb-8 text-2xl sm:text-3xl font-bold text-center">Регистрация на {APP_CONFIG.NAME}е</div>

                <Form.Item<RegisterFormData>
                    name="login"
                    rules={[
                        { required: true, message: 'Введите корректный логин' },
                        { min: VALIDATION_CONFIG.USERNAME.MIN_LENGTH, message: `Минимальная длина ${VALIDATION_CONFIG.USERNAME.MIN_LENGTH} символов` },
                        { max: VALIDATION_CONFIG.USERNAME.MAX_LENGTH, message: `Максимальная длина ${VALIDATION_CONFIG.USERNAME.MAX_LENGTH} символов` },
                    ]}
                >
                    <Input 
                        prefix={<UserOutlined />} 
                        placeholder="Логин"
                        size="large"
                    />
                </Form.Item>

                <Form.Item<RegisterFormData>
                    name="name"
                    rules={[
                        { required: true, message: 'Введите корректное имя' },
                        { min: VALIDATION_CONFIG.NAME.MIN_LENGTH, message: `Минимальная длина ${VALIDATION_CONFIG.NAME.MIN_LENGTH} символов` },
                        { max: VALIDATION_CONFIG.NAME.MAX_LENGTH, message: `Максимальная длина ${VALIDATION_CONFIG.NAME.MAX_LENGTH} символов` },
                    ]}
                >
                    <Input 
                        prefix={<UserOutlined />} 
                        placeholder="Фамилия Имя"
                        size="large"
                    />
                </Form.Item>

                <Form.Item<RegisterFormData>
                    name="phone"
                    rules={[
                        { required: true, message: 'Введите корректный номер телефона' },
                        { pattern: VALIDATION_CONFIG.PHONE.PATTERN, message: 'Введите корректный номер телефона' }
                    ]}
                >
                    <Input 
                        prefix={<PhoneOutlined />} 
                        placeholder="Телефон"
                        size="large"
                    />
                </Form.Item>

                <Form.Item<RegisterFormData>
                    name="email"
                    rules={[
                        { required: true, message: 'Введите корректную почту' },
                        { type: 'email', message: 'Введите корректную почту' }
                    ]}
                >
                    <Input 
                        prefix={<MailOutlined />} 
                        placeholder="Почта" 
                        size="large"
                    />
                </Form.Item>

                <Form.Item<RegisterFormData>
                    name="password" 
                    dependencies={['password']}
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
                    <span>Уже есть аккаунт?</span>
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
                        Зарегистрироваться на {APP_CONFIG.NAME}е
                    </Button>
                </Form.Item>
            </Form>
        </main>
    );
};

export default RegisterForm; 