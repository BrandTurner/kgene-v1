/**
 * Custom Hooks - Central Export
 *
 * 🎓 LEARNING NOTE: Barrel Exports for Hooks
 *
 * This file re-exports all custom hooks from one place.
 *
 * Usage:
 *   import { useOrganisms, useCreateOrganism } from '@/lib/hooks'
 *
 * Instead of:
 *   import { useOrganisms } from '@/lib/hooks/useOrganisms'
 *   import { useCreateOrganism } from '@/lib/hooks/useCreateOrganism'
 */

// Organism hooks
export { useOrganisms } from './useOrganisms'
export { useCreateOrganism } from './useCreateOrganism'
export { useDeleteOrganism } from './useDeleteOrganism'

/**
 * 🎓 LEARNING NOTE: Hook Naming Conventions
 *
 * React hooks MUST start with "use":
 *   ✅ useOrganisms
 *   ✅ useCreateOrganism
 *   ❌ getOrganisms (this is for API functions)
 *   ❌ organismsHook
 *
 * Why?
 *   - React's linter enforces hook rules (useEffect, useState, etc.)
 *   - Identifies which functions can call other hooks
 *   - Convention makes code more readable
 *
 * Hook rules:
 *   1. Only call hooks at top level (not in loops/conditions)
 *   2. Only call hooks from React functions or custom hooks
 *   3. Hooks must start with "use"
 */

/**
 * TODO: Add more hooks as we build features
 *
 * Future hooks:
 *   - useOrganism (single organism by ID)
 *   - useUpdateOrganism (update organism mutation)
 *   - useGenes (gene list query)
 *   - useProcessProgress (poll job progress)
 *   - ... and more!
 */
