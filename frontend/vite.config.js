import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    watch: {
      usePolling: true,
      interval: 200,
    },
    proxy: {
      '/api': {
        target: process.env.VITE_API_TARGET || 'http://gateway:80',
        changeOrigin: true,
        followRedirects: true,
      }
    }
  }
});

