/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            '@': path.resolve(__dirname, './src'),
        },
    },
    server: {
        port: 5173,
        proxy: {
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
        },
    },
    build: {
        // Split vendor libs into stable chunks so one feature change doesn't
        // invalidate every user's cache, and the initial bundle stays lean.
        rollupOptions: {
            output: {
                manualChunks: {
                    'react-vendor': ['react', 'react-dom', 'react-router-dom'],
                    'query-vendor': [
                        '@tanstack/react-query',
                        '@tanstack/react-query-devtools',
                    ],
                    charts: ['lightweight-charts', 'recharts'],
                    markdown: ['react-markdown'],
                    'radix-vendor': [
                        '@radix-ui/react-dialog',
                        '@radix-ui/react-slot',
                        '@radix-ui/react-tabs',
                        'cmdk',
                    ],
                },
            },
        },
        chunkSizeWarningLimit: 600,
    },
    test: {
        globals: true,
        environment: 'jsdom',
        setupFiles: ['./src/test/setup.ts'],
    },
});
