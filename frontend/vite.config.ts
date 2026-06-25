import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Target 127.0.0.1 (not localhost) so the proxy uses IPv4 and matches a
      // uvicorn bound to 127.0.0.1; "localhost" can resolve to ::1 and fail.
      '/api': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
    },
  },
});
