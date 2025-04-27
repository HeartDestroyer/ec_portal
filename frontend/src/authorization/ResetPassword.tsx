import React from "react";
import { Form, Input, Button, message, Flex } from "antd";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { LockOutlined } from '@ant-design/icons';
import { setNewPassword } from "@/services/authService";
import { NewPasswordFormData } from "@/types/auth.types";

const ResetPassword: React.FC = () => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const [form] = Form.useForm<NewPasswordFormData>();

    const token = searchParams.get('token');
    if (!token) {
        navigate('/login');
        return null;
    }

    const onFinish = async (values: NewPasswordFormData) => {
        try {
            await setNewPassword({ ...values, token });
            message.success(<span className="text-sm sm:text-base">Пароль успешно изменен</span>);
            navigate('/login');
        } catch (error) {
            const apiError = error as { message: string };
            message.error(<span className="text-sm sm:text-base">{apiError.message}</span>);
        }
    };

    return (
        <div className="flex justify-center items-center h-screen px-4">
            <Form<NewPasswordFormData>
                form={form}
                name="reset-password"
                className="flex flex-col w-full max-w-md"
                onFinish={onFinish}
            >
                <div className="mb-8 text-3xl sm:text-4xl font-bold text-center">Новый пароль</div>

                <Form.Item<NewPasswordFormData>
                    name="password"
                    rules={[
                        { required: true, message: 'Обязательное поле' },
                        { min: 6, message: 'Пароль должен быть не менее 6 символов' }
                    ]}
                >
                    <Input.Password className="text-base sm:text-lg" prefix={<LockOutlined />} placeholder="Новый пароль" />
                </Form.Item>

                <Form.Item<NewPasswordFormData>
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
                        Установить новый пароль
                    </Button>
                </Form.Item>

                <Form.Item>
                    <Flex className="text-base sm:text-lg" justify="center" align="center">
                        <Link to="/login" className="text-base sm:text-lg text-blue-400 hover:text-blue-700">
                            Вернуться к входу
                        </Link> 
                    </Flex>
                </Form.Item>
            </Form>
        </div>
    );
};

export default ResetPassword; 