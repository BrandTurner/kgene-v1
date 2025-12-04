/**
 * Vite Configuration
 *
 * 🎓 LEARNING NOTE: What is Vite?
 * Vite (French for "fast") is a modern build tool that's MUCH faster than Webpack/CRA.
 * Key differences from Create React App:
 *   - Dev server starts in ~500ms (vs 15-30s for CRA)
 *   - Hot Module Replacement (HMR) is instant (<50ms)
 *   - Uses native ES modules in dev (no bundling needed)
 *   - Only bundles for production
 */

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'url'

/**
 * 🎓 LEARNING NOTE: ES Modules vs CommonJS
 * This file uses "type": "module" in package.json (ES modules).
 * In ES modules, __dirname doesn't exist.
 * We recreate it using import.meta.url:
 */
const __dirname = path.dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig({
  /**
   * 🎓 PLUGINS: Vite plugins add functionality
   * @vitejs/plugin-react: Enables React Fast Refresh (HMR)
   */
  plugins: [react()],

  /**
   * 🎓 RESOLVE: Configure module resolution
   * This makes @ alias work at runtime (TypeScript handles it at compile time)
   * Example: import { Button } from '@/components/ui/button'
   *          resolves to: ./src/components/ui/button
   */
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
