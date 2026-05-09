import { defineConfig } from "astro/config";

export default defineConfig({
  devToolbar: {
    enabled: false,
  },
  server: {
    host: "0.0.0.0",
    port: 4321,
  },
  vite: {
    optimizeDeps: {
      noDiscovery: true,
      entries: [],
      exclude: ["aria-query", "axobject-query", "astro/toolbar"],
    },
  },
});
