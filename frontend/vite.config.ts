import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

export default defineConfig({
  plugins: [vue(), vueDevTools()],
  server: {
    proxy: {
      '/ws': {
        target: 'https://department-quality-rand-hearts.trycloudflare.com',
        ws: true,
        changeOrigin: true,
        rewrite: (path: string) => path.replace(/^\/ws/, ''),
      },
      '/api': {
        target: 'https://department-quality-rand-hearts.trycloudflare.com',
        changeOrigin: true,
      },
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
})
