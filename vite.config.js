import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    chunkSizeWarningLimit: 1000,
    rollupOptions: { output: { manualChunks: { three: ['three'] } } },
  },
  server: { port: 5180 },
});
