export interface Session {
    id: string;
    user_id: string;
    user_name: string;
    device: string;
    browser: string;
    os: string;
    ip_address: string;
    location: string;
    created_at: string;
    last_activity: string;
    is_active: boolean;
    is_current: boolean;
}
  
export interface SessionsPage {
    total: number;
    page: number;
    page_size: number;
    sessions: Session[];
}

export interface SessionFilter {
    page?: number;
    page_size?: number;
    user_name?: string;
    is_active?: boolean;
}

