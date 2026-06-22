// Change log:
// [#001] 2026-06-22 — Sumeet — Simplified to a plain React+Vite setup for the Unveilix
//         Support UI: dropped the TanStack Router and Tailwind plugins (the app uses a tiny
//         built-in router and plain CSS ported from the mockup) and added a dev proxy so
//         `/api` reaches the backend without CORS during local development.
import path from "node:path"
import react from "@vitejs/plugin-react-swc"
import { defineConfig } from "vite"

// https://vitejs.dev/config/
export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  plugins: [react()],
  server: {
    host: true,
    port: 5180,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
})
