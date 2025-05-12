export type DepartmentType = 1 | 7;

export interface Department {
    id: DepartmentType;
    name: string;
    description?: string;
    created_at: string;
    updated_at: string;
} 