import { defineConfig } from 'vite';

export default defineConfig({
  base: '/',
  build: {
    target: 'es2020',
    outDir: 'dist',
  },
  worker: {
    format: 'es',
  },
  test: {
    environment: 'node',
    testTimeout: 180_000,
    hookTimeout: 180_000,
  },
} as any);
