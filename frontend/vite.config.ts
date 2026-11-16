import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],

  resolve: {
    alias: {
      // Allows: import X from '@/components/X'  from anywhere
      '@': path.resolve(__dirname, './src'),
    },
  },

  server: {
    port: 5173,
    proxy: {
      // Forward only specific backend API paths — NOT /auth/callback
      // which is a React Router page (the OAuth callback handler).
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // Backend OAuth routes (exchange code, get current user)
      '/auth/github': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/auth/me': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/webhooks': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
