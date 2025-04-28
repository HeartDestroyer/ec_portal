import React from "react";
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

    const onFinish = async (values: RegisterFormData) => {
        try {
            await register(values);
            navigate(APP_CONFIG.ROUTES.PUBLIC.LOGIN);
        } catch (error) {
            console.log("Ошибка регистрации", error);
        }
    };

    return (
        <div className="flex justify-center items-center h-screen px-4">
            <Form<RegisterFormData>
                form={form}
                name="register"
                layout="vertical"
                initialValues={{ remember: true }}
                className="flex flex-col w-full max-w-md"
                onFinish={onFinish}
                validateTrigger={['onChange', 'onBlur']}
                autoComplete="off"
            >
                <div className="mb-8 text-3xl sm:text-4xl font-bold text-center">Регистрация на {APP_CONFIG.NAME}е</div>

                <Form.Item<RegisterFormData>
                    name="login"
                    label="Логин"
                    rules={[
                        { required: true, message: 'Обязательное поле' },
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
                    label="Фамилия Имя"
                    rules={[
                        { required: true, message: 'Обязательное поле' },
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
                    label="Телефон"
                    rules={[
                        { required: true, message: 'Обязательное поле' },
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
                    label="Почта"
                    rules={[
                        { required: true, message: 'Обязательное поле' },
                        { type: 'email', message: 'Введите корректный email' }
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
                    label="Пароль"
                    dependencies={['password']}
                    rules={[
                        { required: true, message: 'Обязательное поле' },
                        { min: VALIDATION_CONFIG.PASSWORD.MIN_LENGTH, message: `Минимальная длина ${VALIDATION_CONFIG.PASSWORD.MIN_LENGTH} символов` },
                        { max: VALIDATION_CONFIG.PASSWORD.MAX_LENGTH, message: `Максимальная длина ${VALIDATION_CONFIG.PASSWORD.MAX_LENGTH} символов` },
                        { pattern: VALIDATION_CONFIG.PASSWORD.PATTERN, message: 'Пароль должен содержать заглавные и строчные буквы, цифры и специальные символы' }
                    ]}
                >
                    <Input.Password 
                        className="text-base sm:text-lg" 
                        prefix={<LockOutlined />} 
                        placeholder="Пароль"
                        size="large"
                    />
                </Form.Item>

                <Form.Item>
                    <Button 
                        type="primary"
                        htmlType="submit"
                        block
                        size="large"
                    >
                        Зарегистрироваться
                    </Button>
                </Form.Item>

                <Form.Item>
                    <div className="text-lg flex flex-row items-center justify-between">
                        <div>Уже есть аккаунт?</div>
                        <Link to={APP_CONFIG.ROUTES.PUBLIC.LOGIN}>
                            Войти
                        </Link> 
                    </div>
                </Form.Item>
            </Form>
        </div>
    );
};

export default RegisterForm; 