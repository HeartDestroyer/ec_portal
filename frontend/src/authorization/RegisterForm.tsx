import React from "react";
import { Form, Input, Button, message, Flex } from "antd";
import { Link, useNavigate } from "react-router-dom";
import { UserOutlined, MailOutlined, LockOutlined } from '@ant-design/icons';
import { register } from "@/services/authService";
import { RegisterFormData } from "@/types/auth.types";

const RegisterForm: React.FC = () => {
    const navigate = useNavigate();
    const [form] = Form.useForm<RegisterFormData>();

    const onFinish = async (values: RegisterFormData) => {
        try {
            const response = await register(values);
            localStorage.setItem('token', response.accessToken);
            message.success(<span className="text-sm sm:text-base">Регистрация успешна</span>);
            navigate("/dashboard");
        } catch (error) {
            const apiError = error as { message: string };
            message.error(<span className="text-sm sm:text-base">{apiError.message}</span>);
        }
    };

    return (
        <div className="flex justify-center items-center h-screen px-4">
            <Form<RegisterFormData>
                form={form}
                name="register"
                className="flex flex-col w-full max-w-md"
                onFinish={onFinish}
            >
                <div className="mb-8 text-3xl sm:text-4xl font-bold text-center">Регистрация</div>

                <Form.Item<RegisterFormData>
                    name="username"
                    rules={[{ required: true, message: 'Обязательное поле' }]}
                >
                    <Input className="text-base sm:text-lg" prefix={<UserOutlined />} placeholder="Логин" />
                </Form.Item>

                <Form.Item<RegisterFormData>
                    name="email"
                    rules={[
                        { required: true, message: 'Обязательное поле' },
                        { type: 'email', message: 'Введите корректный email' }
                    ]}
                >
                    <Input className="text-base sm:text-lg" prefix={<MailOutlined />} placeholder="Email" />
                </Form.Item>

                <Form.Item<RegisterFormData>
                    name="password"
                    rules={[
                        { required: true, message: 'Обязательное поле' },
                        { min: 6, message: 'Пароль должен быть не менее 6 символов' }
                    ]}
                >
                    <Input.Password className="text-base sm:text-lg" prefix={<LockOutlined />} placeholder="Пароль" />
                </Form.Item>

                <Form.Item<RegisterFormData>
                    name="confirmPassword"
                    dependencies={['password']}
                    rules={[
                        { required: true, message: 'Обязательное поле' },
                        ({ getFieldValue }) => ({
                            validator(_, value) {
                                if (!value || getFieldValue('password') === value) {
                                    return Promise.resolve();
                                }
                                return Promise.reject(new Error('Пароли не совпадают'));
                            },
                        }),
                    ]}
                >
                    <Input.Password className="text-base sm:text-lg" prefix={<LockOutlined />} placeholder="Подтвердите пароль" />
                </Form.Item>

                <Form.Item>
                    <Button className="text-lg h-10" block type="primary" htmlType="submit">
                        Зарегистрироваться
                    </Button>
                </Form.Item>

                <Form.Item>
                    <Flex className="text-base sm:text-lg" justify="center" align="center">
                        Уже есть аккаунт?   
                        <Link to="/login" className="text-base sm:text-lg ml-2 text-blue-400 hover:text-blue-700">
                            Войти
                        </Link> 
                    </Flex>
                </Form.Item>
            </Form>
        </div>
    );
};

export default RegisterForm; 