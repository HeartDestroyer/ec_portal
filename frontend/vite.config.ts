import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { visualizer } from 'rollup-plugin-visualizer';
import path from 'path';

export default defineConfig({
    plugins: [
        react(),
        tailwindcss(),
        visualizer({
            open: true, 		// автоматически откроет отчет после сборки
            gzipSize: true, 	// покажет размеры после gzip-сжатия
            brotliSize: true 	// покажет размеры после brotli-сжатия
        })
    ],
    resolve: {
        alias: {
            '@': path.resolve(__dirname, './src'),
            '@services': path.resolve(__dirname, './src/services'),
            '@types': path.resolve(__dirname, './src/types'),
            '@components': path.resolve(__dirname, './src/components'),
            '@hooks': path.resolve(__dirname, './src/hooks'),
            '@context': path.resolve(__dirname, './src/context'),
            '@utils': path.resolve(__dirname, './src/utils'),
            '@config': path.resolve(__dirname, './src/config'),
            '@assets': path.resolve(__dirname, './src/assets')
        }
    }
})
