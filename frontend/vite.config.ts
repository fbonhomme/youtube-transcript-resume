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
      // Dev admin access relies on Vite listening on localhost only: never
      // start it with `--host` / `server.host: true`, which would expose
      // the admin API to the network, since proxied requests reach the
      // backend from 127.0.0.1.
      '^/(summaries|themes|search|prompts|stats|models|admin-api)/': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/health': 'http://localhost:8000',
    },
  },
})
