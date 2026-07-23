import { defineConfig } from 'vite';
import { resolve } from 'path';

// Main Vite configuration for the study application frontend
export default defineConfig({
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:7800',
        changeOrigin: true
      }
    }
  },

  // Path aliases for cleaner imports
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
      '/js': resolve(__dirname, './src/js'),
      '/styles': resolve(__dirname, './src/css')
    }
  },

  build: {
    outDir: 'dist',
    sourcemap: true,
    assetsDir: 'assets',

    rollupOptions: {
      // Multi-page application entry points
      input: {
        main: resolve(__dirname, 'index.html'),
        consent: resolve(__dirname, 'consent.html'),
        pre_study: resolve(__dirname, 'pre-study.html'),
        post_study: resolve(__dirname, 'post-study.html'),
        study: resolve(__dirname, 'study.html'),
        study_explanation: resolve(__dirname, 'study-explanation.html'),
        finish: resolve(__dirname, 'finish.html'),
        token: resolve(__dirname, 'token.html'),
        navbar: resolve(__dirname, 'navbar.html'),
        footer: resolve(__dirname, 'footer.html'),
        error_modal: resolve(__dirname, 'error-modal.html'),
        bug_report_modal: resolve(__dirname, 'bug-report-modal.html'),
        already_completed: resolve(__dirname, 'already-completed.html'),
        token_expired: resolve(__dirname, 'token-expired.html')
      },

      output: {
        // Asset handling and directory structure configuration
        assetFileNames: (assetInfo) => {
          const fileName = assetInfo?.fileName || assetInfo?.name || '';
          const info = fileName.split('.');
          const ext = info[info.length - 1];

          // Route different asset types to their respective directories
          if (/\.(mp4|webm|ogg|mp3|wav|flac|aac)(\?.*)?$/i.test(fileName)) {
            return `assets/media/[name]-[hash][extname]`;
          }
          if (/\.(png|jpe?g|gif|svg|ico|webp)(\?.*)?$/i.test(fileName)) {
            return `assets/images/[name]-[hash][extname]`;
          }
          if (/\.(woff2?|eot|ttf|otf)(\?.*)?$/i.test(fileName)) {
            return `assets/fonts/[name]-[hash][extname]`;
          }
          if (ext === 'css') {
            return `assets/css/[name]-[hash][extname]`;
          }
          return `assets/[name]-[hash][extname]`;
        },
        chunkFileNames: 'assets/js/[name]-[hash].js',
        entryFileNames: 'assets/js/[name]-[hash].js'
      }
    },

    // Build optimization settings
    cssCodeSplit: true,
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: false,
        drop_debugger: true
      }
    }
  },

  // CSS processing configuration
  css: {
    modules: {
      localsConvention: 'camelCase'
    },
    preprocessorOptions: {
      css: {
        charset: false
      }
    }
  }
}); 