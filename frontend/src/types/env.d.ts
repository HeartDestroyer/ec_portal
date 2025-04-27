interface ImportMetaEnv {
    readonly BACKEND_URL: string;
    readonly FRONTEND_URL: string;
}

interface ImportMeta {
    readonly env: ImportMetaEnv;
} 