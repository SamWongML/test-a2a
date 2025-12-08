import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Use environment variable for API URL (Docker: http://orchestrator:8000, Local: http://localhost:8000)
const apiTarget = process.env.VITE_API_URL || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/stream': {
        target: apiTarget,
        changeOrigin: true
      }
    }
  }
})
