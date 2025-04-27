import React, { useState } from "react";
import { Form, Input, Button, Checkbox, message, Flex } from "antd";
import { Link, useNavigate } from "react-router-dom";
import { LockOutlined, UserOutlined } from '@ant-design/icons';
import { useAuth } from "@/context/AuthContext";
import { LoginFormData } from "@/types/auth.types";
import { VALIDATION_CONFIG } from "@/config/app.config";

const LoginForm: React.FC = () => {
    const navigate = useNavigate();
    const { login } = useAuth();
    const [form] = Form.useForm<LoginFormData>();
    const [isSubmitting, setIsSubmitting] = useState(false);

    const onFinish = async (values: LoginFormData) => {
        try {
            setIsSubmitting(true);
            await login(values);
            message.success(<span className="text-sm sm:text-base">Успешный вход</span>);
            navigate("/dashboard");
        } catch (error) {
            const apiError = error as { message: string };
            message.error(<span className="text-sm sm:text-base">{apiError.message}</span>);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="flex justify-center items-center h-screen px-4">
            <Form<LoginFormData>
                form={form}
                name="login"
                initialValues={{
                    remember: true,
                }}
                className="flex flex-col w-full max-w-md"
                onFinish={onFinish}
                validateTrigger={['onChange', 'onBlur']}
            >
                <div className="mb-8 text-3xl sm:text-4xl font-bold text-center">ЭЦ-портал</div>

                <Form.Item<LoginFormData>
                    name="username"
                    rules={[
                        { required: true, message: 'Обязательное поле' },
                        { 
                            min: VALIDATION_CONFIG.USERNAME.MIN_LENGTH, 
                            message: `Минимальная длина ${VALIDATION_CONFIG.USERNAME.MIN_LENGTH} символов` 
                        },
                        { 
                            max: VALIDATION_CONFIG.USERNAME.MAX_LENGTH, 
                            message: `Максимальная длина ${VALIDATION_CONFIG.USERNAME.MAX_LENGTH} символов` 
                        },
                        { 
                            pattern: VALIDATION_CONFIG.USERNAME.PATTERN, 
                            message: 'Только латинские буквы, цифры и подчеркивание' 
                        }
                    ]}
                >
                    <Input 
                        className="text-base sm:text-lg" 
                        prefix={<UserOutlined />} 
                        placeholder="Логин" 
                    />
                </Form.Item>

                <Form.Item<LoginFormData>
                    name="password"
                    rules={[
                        { required: true, message: 'Обязательное поле' },
                        { 
                            min: VALIDATION_CONFIG.PASSWORD.MIN_LENGTH, 
                            message: `Минимальная длина ${VALIDATION_CONFIG.PASSWORD.MIN_LENGTH} символов` 
                        },
                        { 
                            max: VALIDATION_CONFIG.PASSWORD.MAX_LENGTH, 
                            message: `Максимальная длина ${VALIDATION_CONFIG.PASSWORD.MAX_LENGTH} символов` 
                        },
                        { 
                            pattern: VALIDATION_CONFIG.PASSWORD.PATTERN, 
                            message: 'Пароль должен содержать заглавные и строчные буквы, цифры и специальные символы' 
                        }
                    ]}
                >
                    <Input.Password 
                        className="text-base sm:text-lg" 
                        prefix={<LockOutlined />} 
                        placeholder="Пароль" 
                    />
                </Form.Item>

                <Form.Item>
                    <Flex justify="space-between" align="center">
                        <Form.Item name="remember" valuePropName="checked" noStyle>
                            <Checkbox className="text-base sm:text-lg">Запомнить меня</Checkbox>
                        </Form.Item>
                        <Link to="/reset-password" className="text-base sm:text-lg text-blue-400 hover:text-blue-700">
                            Забыли пароль
                        </Link>
                    </Flex>
                </Form.Item>

                <Form.Item>
                    <Button 
                        className="text-lg h-10" 
                        block 
                        type="primary" 
                        htmlType="submit"
                        loading={isSubmitting}
                    >
                        Войти на ЭЦ-портал
                    </Button>
                </Form.Item>

                <Form.Item>
                    <Flex className="text-base sm:text-lg" justify="space-between" align="center">
                        Нет аккаунта?   
                        <Link to="/register" className="text-base sm:text-lg my-auto text-blue-400 hover:text-blue-700">
                            Зарегистрируйтесь
                        </Link> 
                    </Flex>
                </Form.Item>
            </Form>
        </div>
    );
};

export default LoginForm; 