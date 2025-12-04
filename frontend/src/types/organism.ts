/**
 * Organism Type Definitions
 *
 * 🎓 LEARNING NOTE: TypeScript Interfaces
 *
 * What is an interface?
 * - Defines the "shape" of an object (what properties it has and their types)
 * - Compile-time only (doesn't exist in JavaScript runtime)
 * - Provides autocomplete and type checking in your editor
 *
 * Example:
 *   const org: Organism = { id: 1, code: "eco", name: "E. coli" }
 *   org.code  // ✅ TypeScript knows this exists and is a string
 *   org.foo   // ❌ TypeScript error: Property 'foo' doesn't exist
 */

/**
 * 🎓 LEARNING NOTE: Optional Fields (?)
 *
 * Fields with ? are optional - they can be present or undefined:
 *   status?: string  means  status: string | undefined
 *
 * When accessing optional fields, TypeScript forces you to check:
 *   if (organism.status) { ... }  // ✅ Safe
 *   organism.status.toUpperCase() // ❌ Error: might be undefined
 */

/**
 * 🎓 LEARNING NOTE: Union Types (|)
 *
 * Union types mean "one of these values":
 *   status?: "pending" | "complete" | "error"
 *
 * This means status can ONLY be:
 *   - undefined (because of ?)
 *   - "pending"
 *   - "complete"
 *   - "error"
 *
 * TypeScript will error if you try: status = "foo"  // ❌ Not in union
 */

/**
 * Organism - Full organism object from API
 *
 * Matches backend schema: backend/app/schemas/organism.py - Organism
 *
 * This is what you get from:
 *   - GET /api/organisms (array of these)
 *   - GET /api/organisms/{id} (single)
 *   - POST /api/organisms (returns created organism)
 */
export interface Organism {
  /** Primary key from database */
  id: number;

  /** KEGG organism code (3-4 lowercase letters) */
  code: string;

  /** Full organism name (e.g., "Escherichia coli K-12 MG1655") */
  name: string;

  /** Processing status - only exists if organism has been processed */
  status?: "pending" | "complete" | "error";

  /** Background job ID from ARQ worker */
  job_id?: string;

  /** Error message if processing failed */
  job_error?: string;

  /** ISO 8601 timestamp when organism was created */
  created_at: string;

  /** ISO 8601 timestamp when organism was last updated */
  updated_at?: string;
}

/**
 * OrganismCreate - Data to create a new organism
 *
 * Matches backend schema: backend/app/schemas/organism.py - OrganismCreate
 *
 * Use this when:
 *   - POST /api/organisms (create new organism)
 *
 * Example:
 *   const newOrg: OrganismCreate = {
 *     code: "eco",
 *     name: "Escherichia coli K-12 MG1655"
 *   }
 */
export interface OrganismCreate {
  /** KEGG organism code (3-4 lowercase letters, e.g., "eco", "hsa") */
  code: string;

  /** Full organism name */
  name: string;
}

/**
 * OrganismUpdate - Data to update an existing organism
 *
 * Matches backend schema: backend/app/schemas/organism.py - OrganismUpdate
 *
 * 🎓 LEARNING NOTE: All fields optional for PATCH/PUT
 * This allows partial updates - you only send fields you want to change.
 *
 * Use this when:
 *   - PUT /api/organisms/{id} (update organism)
 *
 * Example:
 *   const update: OrganismUpdate = { name: "Updated name" }  // Only update name
 */
export interface OrganismUpdate {
  code?: string;
  name?: string;
  status?: "pending" | "complete" | "error";
  job_error?: string;
}

/**
 * OrganismFilters - Query parameters for filtering organism list
 *
 * Matches backend: backend/app/schemas/filters.py - OrganismListParams
 *
 * Use this when:
 *   - GET /api/organisms?status=complete&code_pattern=eco
 *
 * All fields are optional - you can filter by any combination.
 *
 * Example:
 *   const filters: OrganismFilters = {
 *     status: "complete",
 *     code_pattern: "eco"
 *   }
 */
export interface OrganismFilters {
  /** Filter by processing status */
  status?: "pending" | "complete" | "error";

  /** Filter by organism code (partial match, case-insensitive) */
  code_pattern?: string;

  /** Filter by organism name (partial match, case-insensitive) */
  name_pattern?: string;

  /** Filter organisms created after this date (ISO 8601) */
  created_after?: string;

  /** Filter organisms created before this date (ISO 8601) */
  created_before?: string;

  /** Sort field */
  sort_by?: "name" | "code" | "created_at" | "updated_at";

  /** Sort order */
  order?: "asc" | "desc";

  /** Pagination: Number of records to skip */
  skip?: number;

  /** Pagination: Maximum number of records to return (max 1000) */
  limit?: number;
}
