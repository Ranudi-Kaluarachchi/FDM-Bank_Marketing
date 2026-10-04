import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite dev-server configuration.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Forward every /api/* request to the FastAPI backend so the browser
    // talks to a single origin (no CORS issues, no hard-coded backend URL).
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
