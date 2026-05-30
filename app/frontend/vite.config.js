import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/upload": "http://localhost:8000",
      "/garments": "http://localhost:8000",
      "/filters": "http://localhost:8000",
      "/images": "http://localhost:8000",
    },
  },
});
