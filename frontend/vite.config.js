import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath } from 'url'
import path from 'path'
import process from 'process'

const __dirname = fileURLToPath(new URL('.', import.meta.url))
const API = process.env.VITE_API_URL || 'http://localhost:8000'

export default defineConfig({
  // github pages serves the demo from /stockRadar/
  base: process.env.VITE_BASE || '/',
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    proxy: {
      '/api': API,
      '/health': API,
    },
  },
})
