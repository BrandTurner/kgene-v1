/**
 * Tailwind CSS Configuration
 *
 * 🎓 LEARNING NOTE: What is Tailwind?
 * Tailwind is a "utility-first" CSS framework. Instead of writing custom CSS:
 *   - BAD (old way): <div class="my-custom-button"> + custom CSS file
 *   - GOOD (Tailwind): <div class="bg-blue-500 text-white px-4 py-2 rounded">
 *
 * Benefits:
 *   - No naming classes (no more "what should I call this div?")
 *   - No context switching (HTML + CSS in one place)
 *   - Automatic purging (unused styles removed in production)
 *   - Responsive by default (sm:, md:, lg: prefixes)
 */

/** @type {import('tailwindcss').Config} */
export default {
    darkMode: ["class"],
    /**
   * 🎓 CONTENT: Tell Tailwind which files to scan for class names
   * Tailwind needs to know where you use utility classes so it can:
   *   1. Include only the CSS you actually use (tree-shaking)
   *   2. Purge unused styles in production (smaller bundle size)
   */
  content: [
    "./index.html",              // Main HTML file
    "./src/**/*.{js,ts,jsx,tsx}", // All JavaScript/TypeScript files in src/
  ],

  /**
   * 🎓 THEME: Customize Tailwind's default design system
   * We're adding custom colors for our clean, professional scientific UI
   */
  theme: {
  	extend: {
  		colors: {
  			primary: {
  				'50': '#eff6ff',
  				'100': '#dbeafe',
  				'200': '#bfdbfe',
  				'300': '#93c5fd',
  				'400': '#60a5fa',
  				'500': '#3b82f6',
  				'600': '#2563eb',
  				'700': '#1d4ed8',
  				'800': '#1e40af',
  				'900': '#1e3a8a',
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			border: 'hsl(var(--border))',
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			}
  		},
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		}
  	}
  },

  /**
   * 🎓 PLUGINS: Add extra Tailwind functionality
   * We'll add @tailwindcss/forms later for better form styling
   */
  plugins: [require("tailwindcss-animate")],
}

