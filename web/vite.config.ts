import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Proxy API calls to the Flask backend (AI-StockAnalyzer) once it's running.
    proxy: {
      '/api': 'http://localhost:5000',
    },
  },
})
