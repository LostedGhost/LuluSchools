import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Meme politique que vercel.json / netlify.toml, appliquee par `vite preview` pour
// verifier le build de production en local avant deploiement.
const CONTENT_SECURITY_POLICY = [
  "default-src 'self'",
  "script-src 'self' https://*.kkiapay.me",
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "font-src 'self' data: https://fonts.gstatic.com",
  "img-src 'self' data: blob: https://images.pexels.com https://*.tile.openstreetmap.org https://lulufiles-api.onrender.com https://*.kkiapay.me",
  "media-src 'self' blob: https://lulufiles-api.onrender.com",
  "connect-src 'self' https://*.kkiapay.me",
  "frame-src https://*.kkiapay.me",
  "worker-src 'self' blob:",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join('; ')

const apiProxy = {
  '/api': {
    // Surchargeable pour lancer un second environnement local en parallele.
    target: process.env.LULU_API_PROXY ?? 'http://127.0.0.1:8000',
    changeOrigin: true,
    ws: true, // UC-25 : canal temps reel /api/v1/ws/sessions-live/{id}
  },
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: apiProxy },
  preview: {
    proxy: apiProxy,
    headers: { 'Content-Security-Policy': CONTENT_SECURITY_POLICY },
  },
})
