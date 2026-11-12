import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The engine API (server/) runs separately; in development it is proxied under /api.
export default defineConfig({
  plugins: [react()],
  server: { port: 5178, proxy: { '/api': 'http://127.0.0.1:8790' } },
  preview: { port: 5179, proxy: { '/api': 'http://127.0.0.1:8790' } },
  build: { assetsInlineLimit: 0 },
});
