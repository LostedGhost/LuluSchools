import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        // Surchargeable pour lancer un second environnement local en parallele.
        target: process.env.LULU_API_PROXY ?? 'http://127.0.0.1:8000',
        changeOrigin: true,
        ws: true, // UC-25 : canal temps reel /api/v1/ws/sessions-live/{id}
      },
    },
  },
})
