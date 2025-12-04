/**
 * Vitest Test Setup
 *
 * 🎓 LEARNING NOTE: This file runs before ALL tests
 * It configures the testing environment globally.
 */

import '@testing-library/jest-dom'

/**
 * @testing-library/jest-dom
 *
 * 🎓 WHAT IT DOES: Adds custom matchers for DOM assertions
 *
 * Without it:
 *   expect(element.textContent).toBe('Hello')  // Verbose
 *
 * With it:
 *   expect(element).toHaveTextContent('Hello')  // Clean!
 *
 * Custom matchers it provides:
 *   - toBeInTheDocument()  - Element exists in DOM
 *   - toHaveTextContent()  - Element has specific text
 *   - toBeVisible()        - Element is visible (not display:none)
 *   - toBeDisabled()       - Input/button is disabled
 *   - toHaveAttribute()    - Element has attribute
 *   - toHaveClass()        - Element has CSS class
 *   - ... and many more!
 *
 * Docs: https://github.com/testing-library/jest-dom
 */

/**
 * Global test utilities (optional)
 * Add any test helpers here that should be available in all tests
 */

// Example: Mock window.matchMedia (for responsive tests)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {}, // deprecated
    removeListener: () => {}, // deprecated
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
  }),
})
