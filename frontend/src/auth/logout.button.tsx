import React from "react";
import { Button } from "antd";
import { LogoutOutlined } from '@ant-design/icons';

interface LogoutButtonProps {
    onLogout: () => void;
}

const LogoutButton: React.FC<LogoutButtonProps> = ({ onLogout }) => {
    return (
        <Button
            type="text"
            icon={<LogoutOutlined />}
            onClick={onLogout}
            className="text-base"
        >
            Выйти
        </Button>
    );
};

export default LogoutButton; 