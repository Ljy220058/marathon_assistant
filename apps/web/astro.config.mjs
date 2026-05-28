import { defineConfig } from "astro/config";

export default defineConfig({
  devToolbar: {
    enabled: false,
  },
  server: {
    host: "0.0.0.0",
    port: 4321,
    headers: {
      "X-Content-Type-Options": "nosniff",
      "X-Frame-Options": "DENY",
      "Referrer-Policy": "strict-origin-when-cross-origin",
      "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    },
  },
  vite: {
    optimizeDeps: {
      noDiscovery: true,
      entries: [],
      exclude: ["aria-query", "axobject-query", "astro/toolbar"],
    },
  },
});
