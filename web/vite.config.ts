import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

// GitHub Pages 项目站走 --base=/nasdaq-signal/（见 build:pages），本地 dev/preview 用默认 /
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 8510 },
  preview: { port: 8511, host: true },
});
