/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_RESET_DISABLED?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
