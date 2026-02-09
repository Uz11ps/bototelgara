import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'mini_app',
    emptyOutDir: false, // Don't delete existing files in mini_app
  },
})