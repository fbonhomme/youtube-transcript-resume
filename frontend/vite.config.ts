import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Keys starting with "^" are treated as RegExp by Vite. Requiring a
      // trailing slash mirrors nginx.conf so bare client-side routes
      // /themes and /prompts fall through to the SPA on refresh/deep-link
      // in dev, while API calls (always trailing-slash/sub-path) proxy.
      '^/(summaries|themes|search|prompts|stats)/': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/health': 'http://localhost:8000',
    },
  },
})
