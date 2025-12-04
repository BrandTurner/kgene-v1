# Frontend Architecture

This document explains the structure and organization of the KEGG Explore React frontend.

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Directory Organization](#directory-organization)
3. [File Naming Conventions](#file-naming-conventions)
4. [Component Patterns](#component-patterns)
5. [State Management Strategy](#state-management-strategy)
6. [API Client Architecture](#api-client-architecture)
7. [Data Flow](#data-flow)
8. [Error Handling](#error-handling)

---

## Project Structure

```
frontend/
├── public/              # Static assets (served as-is)
│   └── vite.svg        # Favicon
│
├── src/
│   ├── components/     # Reusable UI components
│   │   └── ui/        # Shadcn UI components (auto-generated)
│   │       ├── button.tsx
│   │       ├── dialog.tsx
│   │       ├── input.tsx
│   │       ├── table.tsx
│   │       └── ...
│   │
│   ├── config/        # App-wide configuration
│   │   └── queryClient.ts  # React Query configuration
│   │
│   ├── lib/           # Core business logic
│   │   ├── api/       # API client and endpoints
│   │   │   ├── client.ts     # Axios instance with interceptors
│   │   │   └── organisms.ts  # Organism API methods
│   │   │
│   │   └── hooks/     # Custom React hooks
│   │       ├── useOrganisms.ts        # Query hook
│   │       ├── useCreateOrganism.ts   # Mutation hook
│   │       ├── useDeleteOrganism.ts   # Mutation hook
│   │       └── index.ts               # Re-export all hooks
│   │
│   ├── pages/         # Page components (route targets)
│   │   └── Dashboard.tsx  # Main organism management page
│   │
│   ├── test/          # Test utilities
│   │   └── setup.ts   # Vitest configuration
│   │
│   ├── types/         # TypeScript type definitions
│   │   ├── organism.ts  # Organism interfaces
│   │   ├── error.ts     # Error types
│   │   └── index.ts     # Re-export all types
│   │
│   ├── App.tsx        # Root component with routing
│   ├── main.tsx       # Application entry point
│   ├── index.css      # Global styles (TailwindCSS)
│   └── vite-env.d.ts  # Vite TypeScript definitions
│
├── docs/              # Documentation
│   ├── LEARNING.md    # Learning guide (TypeScript, Vite, React)
│   └── ARCHITECTURE.md # This file
│
├── .env.development   # Development environment variables
├── .nvmrc             # Node.js version (24.11.1)
├── components.json    # Shadcn UI configuration
├── index.html         # HTML entry point (loads main.tsx)
├── package.json       # Dependencies and scripts
├── tailwind.config.js # TailwindCSS configuration
├── tsconfig.json      # TypeScript configuration
├── vite.config.ts     # Vite configuration
└── vitest.config.ts   # Test configuration
```

---

## Directory Organization

### `src/components/`

**Purpose:** Reusable UI components that can be used across multiple pages.

**Current structure:**
```
components/
└── ui/  # Shadcn UI components (managed by shadcn CLI)
```

**Future structure (as app grows):**
```
components/
├── ui/               # Shadcn UI primitives
│   ├── button.tsx
│   └── dialog.tsx
│
├── organisms/        # Organism-specific components
│   ├── OrganismTable.tsx
│   ├── OrganismRow.tsx
│   └── OrganismFilterBar.tsx
│
├── genes/            # Gene-specific components
│   ├── GeneTable.tsx
│   └── GeneFilterBar.tsx
│
└── common/           # Shared components
    ├── LoadingSpinner.tsx
    ├── ErrorMessage.tsx
    └── EmptyState.tsx
```

**Rules:**
- Components must be reusable (used in 2+ places)
- Single-use components stay in `pages/`
- Shadcn UI components in `ui/` are auto-generated

---

### `src/config/`

**Purpose:** App-wide configuration that needs to be shared.

**Files:**
- `queryClient.ts` - React Query configuration (cache settings)

**Future additions:**
- `routes.ts` - Route definitions
- `constants.ts` - App constants

**Rules:**
- Only configuration, no business logic
- Must be imported by root components (App, main.tsx)

---

### `src/lib/`

**Purpose:** Core business logic and utilities.

#### `src/lib/api/`

**Purpose:** All API communication logic.

**Files:**
- `client.ts` - Axios instance with interceptors
- `organisms.ts` - Organism CRUD methods
- `genes.ts` - Gene query methods (future)
- `processes.ts` - Process/job methods (future)

**Pattern:**
```typescript
// lib/api/organisms.ts
import { apiClient } from './client'
import type { Organism, OrganismCreate } from '@/types'

export async function getOrganisms(): Promise<Organism[]> {
  const { data } = await apiClient.get<Organism[]>('/organisms')
  return data
}

export async function createOrganism(organism: OrganismCreate): Promise<Organism> {
  const { data } = await apiClient.post<Organism>('/organisms', organism)
  return data
}
```

**Rules:**
- Each API endpoint file exports functions (not classes)
- Always use TypeScript types for parameters and return values
- Use `apiClient` from `client.ts` (not raw axios)
- Functions must be async and return promises

#### `src/lib/hooks/`

**Purpose:** Custom React hooks (mostly React Query wrappers).

**Files:**
- `useOrganisms.ts` - Query hook for fetching organisms
- `useCreateOrganism.ts` - Mutation hook for creating
- `useDeleteOrganism.ts` - Mutation hook for deleting
- `index.ts` - Barrel export (re-exports all hooks)

**Pattern:**
```typescript
// lib/hooks/useOrganisms.ts
import { useQuery } from '@tanstack/react-query'
import { getOrganisms } from '@/lib/api/organisms'

export function useOrganisms() {
  return useQuery({
    queryKey: ['organisms'],
    queryFn: getOrganisms,
  })
}
```

**Rules:**
- One hook per file
- Hook names must start with `use`
- Query hooks for GET (read data)
- Mutation hooks for POST/PUT/DELETE (change data)
- Export from `index.ts` for clean imports

**Import pattern:**
```typescript
// ✅ Good (barrel import)
import { useOrganisms, useCreateOrganism } from '@/lib/hooks'

// ❌ Bad (direct imports)
import { useOrganisms } from '@/lib/hooks/useOrganisms'
import { useCreateOrganism } from '@/lib/hooks/useCreateOrganism'
```

---

### `src/pages/`

**Purpose:** Top-level page components (route targets).

**Current:**
- `Dashboard.tsx` - Main organism list page

**Future:**
- `OrganismDetail.tsx` - Single organism view
- `GeneBrowser.tsx` - Gene search and filtering
- `ProcessMonitor.tsx` - Job progress tracking

**Rules:**
- One page per route
- Pages can import components from `components/`
- Pages can contain single-use components inline
- Pages use hooks from `lib/hooks/`

**Pattern:**
```typescript
// pages/Dashboard.tsx
export default function Dashboard() {
  const { data: organisms, isLoading } = useOrganisms()

  if (isLoading) return <LoadingSpinner />

  return (
    <div>
      <h1>Dashboard</h1>
      <OrganismTable data={organisms} />
    </div>
  )
}
```

---

### `src/types/`

**Purpose:** TypeScript type definitions (interfaces, types, enums).

**Files:**
- `organism.ts` - Organism-related types
- `gene.ts` - Gene-related types (future)
- `process.ts` - Process/job types (future)
- `error.ts` - Error types
- `index.ts` - Barrel export

**Pattern:**
```typescript
// types/organism.ts
export interface Organism {
  id: number
  code: string
  name: string
  status?: "pending" | "complete" | "error"
  created_at: string
}

export interface OrganismCreate {
  code: string
  name: string
}

export interface OrganismFilters {
  status?: "pending" | "complete" | "error"
  code_pattern?: string
  name_pattern?: string
}
```

**Rules:**
- Match backend API schemas exactly
- One entity per file (organism.ts, gene.ts, etc.)
- Use `interface` for objects, `type` for unions
- Export from `index.ts` for clean imports

**Import pattern:**
```typescript
// ✅ Good (barrel import)
import type { Organism, OrganismCreate } from '@/types'

// ❌ Bad (direct import)
import type { Organism } from '@/types/organism'
```

---

## File Naming Conventions

### Components

**Pages:** PascalCase
```
Dashboard.tsx
OrganismDetail.tsx
GeneBrowser.tsx
```

**Components:** PascalCase
```
OrganismTable.tsx
GeneFilterBar.tsx
LoadingSpinner.tsx
```

**Shadcn UI:** lowercase with hyphens
```
button.tsx
dialog.tsx
input.tsx
```

### Non-Components

**API files:** lowercase
```
organisms.ts
genes.ts
client.ts
```

**Hooks:** camelCase starting with "use"
```
useOrganisms.ts
useCreateOrganism.ts
```

**Types:** lowercase
```
organism.ts
gene.ts
error.ts
```

**Config:** camelCase
```
queryClient.ts
routes.ts
```

---

## Component Patterns

### Page Component Pattern

**Structure:**
```typescript
export default function PageName() {
  // 1. Hooks (data fetching, state)
  const { data, isLoading, error } = useSomeQuery()
  const [showDialog, setShowDialog] = useState(false)

  // 2. Event handlers
  const handleSubmit = async () => { ... }
  const handleDelete = async () => { ... }

  // 3. Early returns (loading, error states)
  if (isLoading) return <LoadingSpinner />
  if (error) return <ErrorMessage error={error} />

  // 4. Main render
  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1>Page Title</h1>
        <Button onClick={...}>Action</Button>
      </div>

      {/* Content */}
      <Card>
        <Table>...</Table>
      </Card>

      {/* Dialogs/Modals */}
      <Dialog open={showDialog}>...</Dialog>
    </div>
  )
}
```

### Custom Hook Pattern

**Query hooks (read data):**
```typescript
import { useQuery } from '@tanstack/react-query'
import { getResource } from '@/lib/api/resource'

export function useResource(id?: number) {
  return useQuery({
    queryKey: id ? ['resource', id] : ['resources'],
    queryFn: () => getResource(id),
    enabled: !!id,  // Only run if id exists
  })
}
```

**Mutation hooks (change data):**
```typescript
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createResource } from '@/lib/api/resource'

export function useCreateResource() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: createResource,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resources'] })
    },
  })
}
```

---

## State Management Strategy

We use **two types of state**:

### 1. Server State (React Query)

**What:** Data from the backend API
**Managed by:** React Query (`@tanstack/react-query`)
**Where:** `lib/hooks/` directory

**Examples:**
- List of organisms
- Gene data
- Process status

**Why React Query?**
- Automatic caching
- Background refetching
- Deduplication
- Loading/error states
- TypeScript support

**Usage:**
```typescript
// Query (read data)
const { data: organisms, isLoading, error } = useOrganisms()

// Mutation (change data)
const createMutation = useCreateOrganism()
await createMutation.mutateAsync({ code: 'eco', name: 'E. coli' })
```

### 2. Client State (useState)

**What:** UI state (not synced with backend)
**Managed by:** React `useState` hook
**Where:** Component level (not shared across components)

**Examples:**
- Dialog open/closed
- Form draft values
- Selected tab
- Filter inputs (before submission)

**Usage:**
```typescript
const [showDialog, setShowDialog] = useState(false)
const [formData, setFormData] = useState({ code: '', name: '' })
```

### State Hierarchy

```
┌─────────────────────────────────┐
│ React Query (Server State)     │
│ - Organisms list                │
│ - Gene data                     │
│ - Process status                │
│                                 │
│ Global cache (shared across     │
│ all components)                 │
└─────────────────────────────────┘
           ↓ API calls
┌─────────────────────────────────┐
│ Backend API (FastAPI)           │
│ http://localhost:8000           │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ useState (Client State)         │
│ - Dialog visibility             │
│ - Form inputs                   │
│ - Selected items                │
│                                 │
│ Component-local (not shared)    │
└─────────────────────────────────┘
```

**Rule:** If data comes from API → React Query. If UI-only → useState.

---

## API Client Architecture

### Overview

```
Components/Pages
      ↓
Custom Hooks (useOrganisms, useCreateOrganism)
      ↓
API Methods (getOrganisms, createOrganism)
      ↓
Axios Client (with interceptors)
      ↓
Backend API (FastAPI)
```

### Axios Client (`lib/api/client.ts`)

**Features:**
- Base URL from environment variable
- Request interceptor: Adds `X-Request-ID` header
- Response interceptor: Transforms errors into `ApiError` class
- TypeScript generic support

**Request flow:**
```
1. Component calls: createMutation.mutate({ code: 'eco', name: 'E. coli' })
                     ↓
2. Hook calls:      createOrganism({ code: 'eco', name: 'E. coli' })
                     ↓
3. API method:      apiClient.post<Organism>('/organisms', data)
                     ↓
4. Request interceptor: Adds X-Request-ID header
                     ↓
5. HTTP request:    POST http://localhost:8000/api/organisms
                     ↓
6. Backend response: { id: 1, code: 'eco', name: 'E. coli', ... }
                     ↓
7. Response interceptor: (no error, pass through)
                     ↓
8. Return data:     { id: 1, code: 'eco', name: 'E. coli', ... }
                     ↓
9. Hook onSuccess:  Invalidates ['organisms'] cache
                     ↓
10. Component:      Re-renders with new data
```

**Error flow:**
```
1-5. Same as above
                     ↓
6. Backend error:   { code: 'DUPLICATE_ORGANISM', message: '...', correlation_id: '...' }
                     ↓
7. Response interceptor: Transforms to ApiError
                     ↓
8. Throw error:     throw new ApiError(message, code, statusCode, correlationId)
                     ↓
9. Component catch: Display error toast with correlation ID
```

### API Method Pattern

**File:** `lib/api/organisms.ts`

```typescript
import { apiClient } from './client'
import type { Organism, OrganismCreate } from '@/types'

// GET /api/organisms
export async function getOrganisms(): Promise<Organism[]> {
  const { data } = await apiClient.get<Organism[]>('/organisms')
  return data
}

// POST /api/organisms
export async function createOrganism(organism: OrganismCreate): Promise<Organism> {
  const { data } = await apiClient.post<Organism>('/organisms', organism)
  return data
}

// DELETE /api/organisms/{id}
export async function deleteOrganism(id: number): Promise<void> {
  await apiClient.delete(`/organisms/${id}`)
}
```

**Rules:**
- One function per endpoint
- Always use TypeScript types
- Return unwrapped data (not full axios response)
- Use REST conventions (GET/POST/PUT/DELETE)

---

## Data Flow

### Read Data (Query)

**Example:** Fetching organisms list

```
1. Dashboard.tsx
   └─ const { data: organisms } = useOrganisms()

2. useOrganisms.ts
   └─ return useQuery({ queryKey: ['organisms'], queryFn: getOrganisms })

3. organisms.ts
   └─ return apiClient.get<Organism[]>('/organisms')

4. client.ts
   └─ axios.get('http://localhost:8000/api/organisms')

5. Backend API
   └─ Returns: [{ id: 1, code: 'eco', ... }, ...]

6. React Query Cache
   └─ Stores: ['organisms'] → [{ id: 1, ... }, ...]

7. Component Re-renders
   └─ organisms = [{ id: 1, ... }, ...]
```

**On next mount:**
```
1. Dashboard.tsx (mount again)
   └─ const { data: organisms } = useOrganisms()

2. React Query Cache
   └─ Data is fresh (< 5 min) → Return cached data immediately
   └─ No loading spinner!

3. Background refetch (if stale)
   └─ Fetch fresh data silently
   └─ Update cache
   └─ Re-render if data changed
```

### Write Data (Mutation)

**Example:** Creating an organism

```
1. Dashboard.tsx
   └─ const createMutation = useCreateOrganism()
   └─ await createMutation.mutateAsync({ code: 'eco', name: 'E. coli' })

2. useCreateOrganism.ts
   └─ return useMutation({ mutationFn: createOrganism, ... })

3. organisms.ts
   └─ return apiClient.post<Organism>('/organisms', data)

4. client.ts
   └─ axios.post('http://localhost:8000/api/organisms', data)

5. Backend API
   └─ Creates organism, returns: { id: 1, code: 'eco', ... }

6. useCreateOrganism.ts (onSuccess)
   └─ queryClient.invalidateQueries({ queryKey: ['organisms'] })

7. React Query Cache
   └─ Marks ['organisms'] as stale
   └─ Refetches organisms list

8. Dashboard.tsx
   └─ Re-renders with updated list
```

---

## Error Handling

### Error Flow

```
Backend Error
      ↓
Response Interceptor (client.ts)
      ↓
Transform to ApiError class
      ↓
Throw error
      ↓
Component catch block
      ↓
Display toast with correlation ID
```

### ApiError Class

**Defined in:** `types/error.ts`

```typescript
export class ApiError extends Error {
  code: string              // Error code (DUPLICATE_ORGANISM, etc.)
  statusCode: number        // HTTP status (400, 404, 500)
  correlationId?: string    // For tracing request
  timestamp: string         // When error occurred
  details?: Record<string, any>  // Additional context
}
```

### Error Handling Pattern

**In components:**

```typescript
try {
  await createMutation.mutateAsync(formData)

  toast({
    title: 'Success',
    description: 'Organism created successfully',
  })
} catch (error) {
  const apiError = error as ApiError

  // Handle specific error codes
  if (apiError.code === 'DUPLICATE_ORGANISM') {
    toast({
      title: 'Duplicate Organism',
      description: 'This organism code already exists',
      variant: 'destructive',
    })
  } else {
    // Generic error
    toast({
      title: 'Error',
      description: apiError.message,
      variant: 'destructive',
    })
  }

  // Log correlation ID for debugging
  if (apiError.correlationId) {
    console.error('Correlation ID:', apiError.correlationId)
  }
}
```

### Correlation IDs

**Purpose:** Trace requests across frontend and backend logs.

**How it works:**
```
1. Request Interceptor
   └─ Generate UUID: "550e8400-e29b-41d4-a716-446655440000"
   └─ Add header: X-Request-ID

2. Backend
   └─ Receives request with X-Request-ID
   └─ Logs all operations with this ID
   └─ If error, includes in response: correlation_id

3. Response Interceptor
   └─ Extract correlation_id from error
   └─ Store in ApiError.correlationId

4. Component
   └─ Display correlation ID to user
   └─ User reports: "Error with correlation ID: 550e8400-..."

5. Backend Logs
   └─ Search logs for: "550e8400-..."
   └─ Find exact request and error details
```

**Benefits:**
- Quick debugging
- Trace user-reported errors
- Connect frontend actions to backend logs

---

## Summary: Architecture Principles

### 1. Separation of Concerns

- **Components:** UI and user interactions
- **Hooks:** Data fetching logic
- **API methods:** HTTP communication
- **Types:** Type definitions

### 2. Single Responsibility

- Each file has one clear purpose
- Components focus on rendering
- Hooks focus on data management
- API files focus on HTTP requests

### 3. Type Safety

- TypeScript everywhere
- Interfaces match backend schemas
- Generic types for reusability

### 4. Composability

- Small, reusable components
- Custom hooks for shared logic
- Barrel exports for clean imports

### 5. Error Handling

- Centralized error transformation
- Correlation IDs for tracing
- User-friendly error messages

---

**Next:** See `LEARNING.md` for TypeScript/Vite/React concepts and `README.md` for setup instructions.
