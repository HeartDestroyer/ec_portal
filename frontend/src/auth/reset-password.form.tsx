import React from "react";
import { Form, Input, Button, message, Flex } from "antd";
import { Link } from "react-router-dom";
import { MailOutlined } from '@ant-design/icons';
import { resetPassword } from "@services/authService";
import { ResetPasswordFormData } from "@types/auth.types";

const PasswordRecovery: React.FC = () => {
    const [form] = Form.useForm<ResetPasswordFormData>();

    const onFinish = async (values: ResetPasswordFormData) => {
        try {
            await resetPassword(values);
            message.success(<span className="text-sm sm:text-base">Инструкции по восстановлению пароля отправлены на ваш email</span>);
        } catch (error) {
            const apiError = error as { message: string };
            message.error(<span className="text-sm sm:text-base">{apiError.message}</span>);
        }
    };

    return (
        <div className="flex justify-center items-center h-screen px-4">
            <Form<ResetPasswordFormData>
                form={form}
                name="password-recovery"
                className="flex flex-col w-full max-w-md"
                onFinish={onFinish}
            >
                <div className="mb-8 text-3xl sm:text-4xl font-bold text-center">Восстановление пароля</div>

                <Form.Item<ResetPasswordFormData>
                    name="email"
                    rules={[
                        { required: true, message: 'Обязательное поле' },
                        { type: 'email', message: 'Введите корректный email' }
                    ]}
                >
                    <Input className="text-base sm:text-lg" prefix={<MailOutlined />} placeholder="Email" />
                </Form.Item>

                <Form.Item>
                    <Button className="text-lg h-10" block type="primary" htmlType="submit">
                        Отправить инструкции
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

export default PasswordRecovery; 