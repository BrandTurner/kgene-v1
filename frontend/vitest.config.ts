/**
 * Vitest Configuration
 *
 * 🎓 LEARNING NOTE: What is Vitest?
 * Vitest is a modern test framework that's MUCH faster than Jest:
 *   - Uses Vite's transformation pipeline (instant)
 *   - Watch mode is instant (no startup time)
 *   - API compatible with Jest (easy migration)
 *   - Native ES modules support
 *
 * Key differences from Jest:
 *   - Jest: 5-10s startup, slow watch mode
 *   - Vitest: <1s startup, instant watch mode
 */

import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'url'

// 🎓 ES Modules: Recreate __dirname
const __dirname = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  /**
   * 🎓 PLUGINS: Same React plugin as main Vite config
   */
  plugins: [react()],

  /**
   * 🎓 RESOLVE: Import aliases (same as main Vite config)
   */
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },

  /**
   * 🎓 TEST: Vitest-specific configuration
   */
  test: {
    /**
     * Environment: jsdom simulates browser APIs (DOM, window, document)
     * Needed for React component testing
     */
    environment: 'jsdom',

    /**
     * Setup files: Run before each test file
     * We'll create src/test/setup.ts to configure testing-library
     */
    setupFiles: ['./src/test/setup.ts'],

    /**
     * Globals: Enable global test functions (describe, it, expect)
     * Like Jest, no need to import in each file
     */
    globals: true,

    /**
     * CSS: Don't transform CSS in tests (faster)
     * We're testing logic, not styles
     */
    css: false,

    /**
     * Coverage: Track test coverage (optional)
     * Run with: npm run test:coverage
     */
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.config.ts',
        '**/*.d.ts',
      ],
    },
  },
})
