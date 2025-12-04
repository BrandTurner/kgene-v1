/**
 * Type Definitions - Central Export
 *
 * 🎓 LEARNING NOTE: Barrel Exports
 *
 * This file re-exports all types from one place.
 * Instead of:
 *   import { Organism } from '@/types/organism'
 *   import { ErrorResponse } from '@/types/error'
 *
 * You can do:
 *   import { Organism, ErrorResponse } from '@/types'
 *
 * This is called a "barrel" export pattern - it barrels together
 * multiple exports into one convenient import location.
 */

// Organism types
export type {
  Organism,
  OrganismCreate,
  OrganismUpdate,
  OrganismFilters,
} from './organism'

// Error types
export type {
  ErrorResponse,
  ValidationErrorDetail,
} from './error'

export { ApiError } from './error'

/**
 * 🎓 LEARNING NOTE: export type vs export
 *
 * - export type { Organism }: Type-only export (erased at runtime)
 * - export { ApiError }: Value export (exists at runtime)
 *
 * ApiError is a class, so it exists at runtime (you can throw it).
 * Organism is an interface, so it only exists at compile time.
 *
 * Using "export type" for interfaces helps TypeScript optimize
 * and prevents accidental runtime usage.
 */
