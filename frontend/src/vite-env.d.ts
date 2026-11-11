/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the API server, e.g. https://tazko-api-dev.example.com. Empty in dev (Vite proxy). */
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
