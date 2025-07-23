import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig({
  plugins: [react()],

  // We REMOVE the `root` option entirely. Vite will operate from the project root.
  // This is the most reliable way to ensure paths are not misinterpreted.

  resolve: {
    alias: {
      // These paths are now unambiguous because they are resolved from the project root.
      "@": path.resolve(__dirname, "./client/src"),
      "@shared": path.resolve(__dirname, "./shared"),
    },
  },

  // No `build.rollupOptions` is needed when `root` is not set this way.
  // Vite will find `client/index.html` via the Express middleware.
  
  // The `server` option can be minimal as Express is in control.
  server: {
    middlewareMode: true,
  },
  appType: 'custom'
});