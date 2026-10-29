import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const apiTarget = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: Object.fromEntries(
      ['/auth', '/metrics', '/atms', '/forecast', '/whatif', '/replenishment', '/alerts', '/dispatch', '/dispatches', '/health']
        .map((path) => [path, { target: apiTarget, changeOrigin: true }]),
    ),
  },
})
