# Learning Guide: TypeScript, Vite, and Modern React (2024)

This guide explains key concepts for someone learning TypeScript, new to Vite, and returning to React after 2-3 years.

---

## Table of Contents

1. [TypeScript Fundamentals](#typescript-fundamentals)
2. [Vite vs Create React App](#vite-vs-create-react-app)
3. [Modern React Patterns (2024 vs 2022)](#modern-react-patterns-2024-vs-2022)
4. [React Query Deep Dive](#react-query-deep-dive)
5. [TailwindCSS Utility-First CSS](#tailwindcss-utility-first-css)
6. [Shadcn UI Components](#shadcn-ui-components)

---

## TypeScript Fundamentals

### What is TypeScript?

TypeScript is JavaScript with **type annotations**. It catches errors at compile time instead of runtime.

```typescript
// JavaScript (no type safety)
function greet(name) {
  return `Hello ${name}`
}
greet(42)  // Works but probably wrong!

// TypeScript (type safety)
function greet(name: string): string {
  return `Hello ${name}`
}
greet(42)  // ❌ Error: Argument of type 'number' is not assignable to 'string'
```

### Interfaces vs Types

**Use `interface` for objects** (extensible, better error messages):

```typescript
interface User {
  id: number
  name: string
  email?: string  // Optional field (can be undefined)
}

const user: User = {
  id: 1,
  name: "John",
  // email is optional, so we can omit it
}
```

**Use `type` for unions, primitives, and complex types**:

```typescript
type Status = "pending" | "complete" | "error"  // Union type
type ID = string | number                        // Union of primitives
type Callback = (value: string) => void          // Function type
```

**Key differences:**

```typescript
// Interfaces can be extended
interface Animal {
  name: string
}

interface Dog extends Animal {
  breed: string
}

// Interfaces can be re-opened (declaration merging)
interface User {
  id: number
}

interface User {
  name: string
}
// Result: User has both id and name

// Types use intersections
type Animal = {
  name: string
}

type Dog = Animal & {
  breed: string
}
```

### Optional Fields (`?`)

```typescript
interface Organism {
  id: number           // Required
  name: string         // Required
  status?: string      // Optional (can be undefined)
  created_at: string   // Required
  updated_at?: string  // Optional
}

// Valid usage
const org1: Organism = { id: 1, name: "E. coli", created_at: "2024-01-01" }
const org2: Organism = { id: 2, name: "Human", created_at: "2024-01-01", status: "complete" }
```

### Union Types (`|`)

Restrict values to specific options:

```typescript
type Status = "pending" | "complete" | "error"

let status: Status = "pending"   // ✅ OK
status = "complete"               // ✅ OK
status = "processing"             // ❌ Error: Not one of the allowed values

// Use in interfaces
interface Organism {
  id: number
  status?: "pending" | "complete" | "error"  // Can be one of these or undefined
}
```

### Generics (`<T>`)

Generics make code reusable with different types:

```typescript
// Without generics (specific type)
function getFirstString(items: string[]): string {
  return items[0]
}

function getFirstNumber(items: number[]): number {
  return items[0]
}

// With generics (reusable!)
function getFirst<T>(items: T[]): T {
  return items[0]
}

const firstString = getFirst<string>(["a", "b", "c"])  // Type: string
const firstNumber = getFirst<number>([1, 2, 3])        // Type: number

// TypeScript can infer the type
const firstString2 = getFirst(["a", "b", "c"])  // TypeScript knows it's string[]
```

**Real example from our codebase:**

```typescript
// Axios generic - tells TypeScript what data type to expect
const { data } = await apiClient.get<Organism[]>('/organisms')
//                                 ^^^^^^^^^^^^^^
//                                 TypeScript now knows data is Organism[]

// React Query generic
const { data: organisms } = useQuery<Organism[]>({
  queryKey: ['organisms'],
  queryFn: getOrganisms,
})
// TypeScript knows organisms is Organism[] | undefined
```

### Type Assertions (`as`)

Tell TypeScript "trust me, I know the type":

```typescript
try {
  await createOrganism(data)
} catch (error) {
  // TypeScript doesn't know what type 'error' is
  // We tell it: "error is an ApiError"
  const apiError = error as ApiError

  console.error(apiError.message)
  console.error(apiError.correlationId)
}
```

**⚠️ Warning:** Type assertions don't change runtime behavior! Use carefully.

### Function Types

```typescript
// Function with typed parameters and return value
function add(a: number, b: number): number {
  return a + b
}

// Arrow function
const add = (a: number, b: number): number => {
  return a + b
}

// Arrow function with implicit return
const add = (a: number, b: number): number => a + b

// Async function
async function fetchData(): Promise<Organism[]> {
  const response = await fetch('/api/organisms')
  return response.json()
}

// Function type in interface
interface Props {
  onSubmit: (value: string) => void
  onChange: (value: string) => void
}
```

### Array Types

```typescript
// Two ways to write array types
const numbers: number[] = [1, 2, 3]
const numbers: Array<number> = [1, 2, 3]  // Same thing

// Array of objects
const organisms: Organism[] = [
  { id: 1, name: "E. coli", created_at: "2024-01-01" },
  { id: 2, name: "Human", created_at: "2024-01-01" },
]

// Array methods are type-safe
organisms.map(org => org.name)        // Type: string[]
organisms.filter(org => org.status)   // Type: Organism[]
organisms.find(org => org.id === 1)   // Type: Organism | undefined
```

### Record Type

Create an object type with specific keys and values:

```typescript
// Record<KeyType, ValueType>
type ErrorMessages = Record<string, string>

const errors: ErrorMessages = {
  DUPLICATE_ORGANISM: "Organism already exists",
  INVALID_CODE: "Code must be 3-4 lowercase letters",
  NOT_FOUND: "Organism not found",
}

// Access is type-safe
const message: string = errors.DUPLICATE_ORGANISM
```

---

## Vite vs Create React App

### Why Vite?

**Create React App (CRA) is deprecated:**
- Last update: April 2022
- No longer maintained
- Slow startup (15-30 seconds)
- Uses outdated Webpack

**Vite is the modern replacement:**
- 30x faster development startup (500ms)
- Instant Hot Module Replacement (HMR)
- Smaller production bundles
- Native ES modules
- Officially recommended by React team

### Key Differences

| Feature | Create React App | Vite |
|---------|------------------|------|
| **Entry Point** | `src/index.js` | `src/main.tsx` |
| **Environment Variables** | `process.env.REACT_APP_X` | `import.meta.env.VITE_X` |
| **Port** | 3000 | 5173 |
| **Config File** | `webpack.config.js` | `vite.config.ts` |
| **Startup Time** | 15-30 seconds | 500ms |
| **HMR Speed** | 1-3 seconds | Instant |

### Environment Variables

**CRA (old way):**
```bash
# .env
REACT_APP_API_URL=http://localhost:8000
```

```javascript
// Access in code
const apiUrl = process.env.REACT_APP_API_URL
```

**Vite (new way):**
```bash
# .env.development
VITE_API_BASE_URL=http://localhost:8000
```

```typescript
// Access in code
const apiUrl = import.meta.env.VITE_API_BASE_URL
```

**Rules:**
- ✅ Must prefix with `VITE_` (not `REACT_APP_`)
- ✅ Use `import.meta.env` (not `process.env`)
- ✅ TypeScript types available via `vite-env.d.ts`

### Entry Point Differences

**CRA:**
```javascript
// src/index.js
import ReactDOM from 'react-dom'
import App from './App'

ReactDOM.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
  document.getElementById('root')
)
```

**Vite:**
```typescript
// src/main.tsx (note .tsx extension!)
import { createRoot } from 'react-dom/client'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
```

**Key changes:**
- Use `createRoot` (React 18 API)
- Import `.tsx` extension explicitly
- TypeScript: `!` operator tells TS "this element definitely exists"

### ES Modules vs CommonJS

**CommonJS (old Node.js style):**
```javascript
// Export
module.exports = { foo: 'bar' }

// Import
const thing = require('./thing')

// __dirname exists globally
console.log(__dirname)
```

**ES Modules (Vite uses this):**
```typescript
// Export
export default { foo: 'bar' }
export const helper = () => {}

// Import
import thing from './thing'
import { helper } from './thing'

// __dirname doesn't exist! Use this instead:
import { fileURLToPath } from 'url'
const __dirname = path.dirname(fileURLToPath(import.meta.url))
```

### Fast Refresh (HMR)

Vite's Hot Module Replacement is **instant**:

```typescript
// Edit this file...
export default function Dashboard() {
  return <div>Hello World</div>  // Change this
}

// ...save the file...
// ...and see the change in browser immediately (< 100ms)
```

**Benefits:**
- Component state is preserved
- No full page reload
- Lightning fast feedback loop

---

## Modern React Patterns (2024 vs 2022)

### The Big Change: Server State Management

**OLD WAY (2022) - DON'T DO THIS:**

```typescript
function Dashboard() {
  const [organisms, setOrganisms] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    fetch('/api/organisms')
      .then(response => response.json())
      .then(data => {
        setOrganisms(data)
        setLoading(false)
      })
      .catch(err => {
        setError(err)
        setLoading(false)
      })
  }, [])

  if (loading) return <div>Loading...</div>
  if (error) return <div>Error: {error.message}</div>

  return (
    <div>
      {organisms.map(org => (
        <div key={org.id}>{org.name}</div>
      ))}
    </div>
  )
}
```

**Problems:**
- ❌ 20+ lines of boilerplate
- ❌ Manual loading/error states
- ❌ No caching (refetch on every mount)
- ❌ No background refetching
- ❌ Race conditions possible
- ❌ No deduplication (multiple components = multiple requests)
- ❌ No retry logic

**NEW WAY (2024) - DO THIS:**

```typescript
function Dashboard() {
  const { data: organisms, isLoading, error } = useOrganisms()

  if (isLoading) return <div>Loading...</div>
  if (error) return <div>Error: {error.message}</div>

  return (
    <div>
      {organisms.map(org => (
        <div key={org.id}>{org.name}</div>
      ))}
    </div>
  )
}
```

**Benefits:**
- ✅ 80% less code
- ✅ Automatic caching
- ✅ Background refetching
- ✅ Automatic retries (3x by default)
- ✅ Deduplication (one request for multiple components)
- ✅ TypeScript support
- ✅ DevTools for debugging

### Server State vs Client State

**Server State** (managed by React Query):
- Data from APIs
- Cached and synced with server
- Examples: User list, settings, gene data

**Client State** (managed by useState):
- UI state (modals open/closed, form inputs)
- Not synced with server
- Examples: Dialog visibility, form draft data

```typescript
function Dashboard() {
  // ✅ Server state - React Query
  const { data: organisms } = useOrganisms()

  // ✅ Client state - useState
  const [showDialog, setShowDialog] = useState(false)
  const [formData, setFormData] = useState({ code: '', name: '' })

  return (
    <div>
      <button onClick={() => setShowDialog(true)}>Create</button>
      <Dialog open={showDialog}>
        <input
          value={formData.name}
          onChange={e => setFormData({ ...formData, name: e.target.value })}
        />
      </Dialog>
    </div>
  )
}
```

### React 18 Features

**createRoot (Concurrent Rendering):**
```typescript
// Old (React 17)
ReactDOM.render(<App />, document.getElementById('root'))

// New (React 18)
createRoot(document.getElementById('root')!).render(<App />)
```

**StrictMode (Development Checks):**
```typescript
<StrictMode>
  <App />
</StrictMode>
```

In development, StrictMode:
- Calls functions twice to catch side effects
- Warns about deprecated APIs
- Helps find bugs early

**You might see console.log twice - this is intentional!**

### Error Boundaries

Catch component errors without crashing the entire app:

```typescript
import { ErrorBoundary } from 'react-error-boundary'

function ErrorFallback({ error }) {
  return (
    <div>
      <h2>Something went wrong</h2>
      <p>{error.message}</p>
      <button onClick={() => window.location.reload()}>
        Reload
      </button>
    </div>
  )
}

function App() {
  return (
    <ErrorBoundary FallbackComponent={ErrorFallback}>
      <Dashboard />
    </ErrorBoundary>
  )
}
```

**What error boundaries catch:**
- ✅ Rendering errors
- ✅ Lifecycle method errors
- ✅ Constructor errors

**What they DON'T catch:**
- ❌ Event handler errors (use try/catch)
- ❌ Async errors (use try/catch)
- ❌ Errors in error boundary itself

### React Router v6 Changes

If you used React Router v5 in 2022, here's what changed:

**Old (v5):**
```typescript
<Switch>
  <Route exact path="/" component={Dashboard} />
  <Route path="/organisms/:id" component={OrganismDetail} />
</Switch>
```

**New (v6):**
```typescript
<Routes>
  <Route path="/" element={<Dashboard />} />
  <Route path="/organisms/:id" element={<OrganismDetail />} />
</Routes>
```

**Key changes:**
- `<Routes>` instead of `<Switch>`
- `element={<Component />}` instead of `component={Component}`
- No more `exact` prop (exact matching is default)
- `useParams()` hook still works the same

---

## React Query Deep Dive

### What is React Query?

React Query is a **server state management library**. It replaces:
- `useState` + `useEffect` for data fetching
- Manual caching logic
- Loading/error state management
- Background refetching

### Core Concepts

#### 1. Queries (Read Data)

```typescript
const { data, isLoading, error, refetch } = useQuery({
  queryKey: ['organisms'],  // Cache key (like a unique ID)
  queryFn: getOrganisms,    // Function that returns a promise
})
```

**Query lifecycle:**
```
Mount → Fetch → Cache → Display
         ↓
    Background refetch (keeps data fresh)
         ↓
    Update cache → Re-render
```

#### 2. Mutations (Write Data)

```typescript
const mutation = useMutation({
  mutationFn: createOrganism,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['organisms'] })
  },
})

// Trigger mutation
mutation.mutate({ code: 'eco', name: 'E. coli' })

// Or with async/await
await mutation.mutateAsync({ code: 'eco', name: 'E. coli' })
```

**Mutation lifecycle:**
```
User action → mutate() → API call → onSuccess/onError → Invalidate queries
```

### Query Keys

Query keys are **cache identifiers**:

```typescript
// Simple key
useQuery({ queryKey: ['organisms'], queryFn: getOrganisms })

// Key with parameters (different cache entry per filter)
useQuery({
  queryKey: ['organisms', filters],
  queryFn: () => getOrganisms(filters)
})

// Examples of different cache entries:
['organisms', { status: 'complete' }]  // Cache entry 1
['organisms', { status: 'pending' }]   // Cache entry 2
['organisms', undefined]               // Cache entry 3
```

**Rule:** If parameters change, include them in query key!

### staleTime vs gcTime (formerly cacheTime)

**staleTime** - How long data is considered "fresh":

```typescript
queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,  // 5 minutes
    },
  },
})
```

**Timeline:**
```
Fetch → Fresh (0-5 min) → Stale (5+ min) → Garbage collect (15+ min)
        └─ Don't refetch    └─ Refetch        └─ Remove from memory
           on mount/focus       on mount/focus
```

**gcTime (garbage collection time)** - How long to keep unused data in memory:

```typescript
gcTime: 1000 * 60 * 10,  // 10 minutes
```

**Example flow:**

```
Time 0:00 - Fetch organisms
Time 0:01 - Navigate away (unmount)
Time 0:02 - Navigate back (mount)
          → Data is still fresh (< 5 min)
          → Show cached data immediately (no loading spinner!)
          → No refetch

Time 5:01 - Navigate back again
          → Data is stale (> 5 min)
          → Show cached data (instant)
          → Refetch in background
          → Update UI when new data arrives

Time 15:01 - Navigate back
           → Data was garbage collected (> 10 min unused)
           → Show loading spinner
           → Fetch data
```

**Benefits:**
- Instant page loads (use cached data)
- Fresh data (background refetch)
- Memory efficient (garbage collect old data)

### Invalidating Queries

Tell React Query "this data is now stale, refetch it":

```typescript
const createMutation = useMutation({
  mutationFn: createOrganism,
  onSuccess: () => {
    // After creating, refetch the list
    queryClient.invalidateQueries({ queryKey: ['organisms'] })
  },
})

// Invalidates ALL organism queries:
// - ['organisms']
// - ['organisms', { status: 'complete' }]
// - ['organisms', { status: 'pending' }]
```

**When to invalidate:**
- After creating data
- After updating data
- After deleting data

### Optimistic Updates

Update UI immediately, before API response:

```typescript
const createMutation = useMutation({
  mutationFn: createOrganism,
  onMutate: async (newOrganism) => {
    // Cancel in-flight queries
    await queryClient.cancelQueries({ queryKey: ['organisms'] })

    // Save previous value for rollback
    const previous = queryClient.getQueryData(['organisms'])

    // Optimistically update cache
    queryClient.setQueryData(['organisms'], (old) => [...old, newOrganism])

    return { previous }
  },
  onError: (error, variables, context) => {
    // Rollback on error
    queryClient.setQueryData(['organisms'], context.previous)
  },
  onSettled: () => {
    // Refetch to sync with server
    queryClient.invalidateQueries({ queryKey: ['organisms'] })
  },
})
```

**We don't use this in MVP** (too complex), but it's powerful for instant UI feedback.

### React Query DevTools

View all queries and their states:

```typescript
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'

<QueryClientProvider client={queryClient}>
  <App />
  <ReactQueryDevtools initialIsOpen={false} />
</QueryClientProvider>
```

**Open DevTools in browser** (bottom-left corner):
- See all queries and their keys
- View cached data
- See stale/fresh status
- Manually trigger refetches
- View query timing

---

## TailwindCSS Utility-First CSS

### What is Utility-First CSS?

Instead of writing custom CSS classes, use **utility classes** directly in JSX:

**Old way (CSS classes):**
```css
/* styles.css */
.card {
  background-color: white;
  border-radius: 0.5rem;
  padding: 1rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}
```

```typescript
<div className="card">Content</div>
```

**New way (Tailwind utilities):**
```typescript
<div className="bg-white rounded-lg p-4 shadow">Content</div>
```

**Benefits:**
- No context switching between files
- No naming things ("card", "container", "wrapper")
- No CSS grows indefinitely
- Tree-shaking removes unused styles

### Common Utility Classes

**Layout:**
```typescript
<div className="flex items-center justify-between">  // Flexbox
<div className="grid grid-cols-3 gap-4">            // Grid
<div className="max-w-7xl mx-auto">                 // Center with max width
```

**Spacing:**
```typescript
<div className="p-4">      // Padding: 1rem (16px)
<div className="px-4">     // Padding left/right: 1rem
<div className="py-6">     // Padding top/bottom: 1.5rem
<div className="m-4">      // Margin: 1rem
<div className="space-y-4"> // Vertical space between children: 1rem
```

**Typography:**
```typescript
<h1 className="text-3xl font-bold text-gray-900">   // 30px, bold, dark gray
<p className="text-sm text-gray-600">               // 14px, medium gray
```

**Colors:**
```typescript
<div className="bg-white">           // Background white
<div className="bg-primary-500">     // Background primary blue
<div className="text-red-600">       // Text red
<div className="border-gray-200">    // Border gray
```

**Responsive Design:**
```typescript
<div className="text-sm md:text-base lg:text-lg">
//              ↑        ↑              ↑
//           Mobile   Tablet (768px)  Desktop (1024px)
```

**Hover States:**
```typescript
<button className="bg-blue-500 hover:bg-blue-600">
//                              ↑
//                        Only on hover
```

### Our Custom Colors

See `tailwind.config.js`:

```typescript
colors: {
  primary: {
    50: '#eff6ff',   // Lightest blue
    500: '#3b82f6',  // Primary blue (main color)
    900: '#1e3a8a',  // Darkest blue
  },
}
```

**Usage:**
```typescript
<Button className="bg-primary-500 hover:bg-primary-600">
<div className="text-primary-700">
```

---

## Shadcn UI Components

### What is Shadcn UI?

**NOT a component library** (like Material-UI or Ant Design).

**IT'S A COLLECTION OF COPY-PASTE COMPONENTS:**
- Components are copied into your `src/components/ui` folder
- You own the code (can modify freely)
- No bloated dependencies
- Built on Radix UI (accessible primitives)
- Styled with TailwindCSS

### Installation

```bash
npx shadcn@latest init    # Initialize
npx shadcn@latest add button  # Add button component
```

**This copies files:**
```
src/components/ui/button.tsx  ← You own this file!
```

### Common Components

#### Button

```typescript
import { Button } from '@/components/ui/button'

<Button>Click me</Button>
<Button variant="destructive">Delete</Button>
<Button variant="outline">Cancel</Button>
<Button size="sm">Small</Button>
<Button disabled>Disabled</Button>
```

#### Dialog (Modal)

```typescript
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

<Dialog open={showDialog} onOpenChange={setShowDialog}>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Create Organism</DialogTitle>
      <DialogDescription>
        Add a new organism for gene analysis
      </DialogDescription>
    </DialogHeader>

    {/* Content here */}

    <DialogFooter>
      <Button onClick={() => setShowDialog(false)}>Cancel</Button>
      <Button type="submit">Create</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

#### Input

```typescript
import { Input } from '@/components/ui/input'

<Input
  placeholder="eco"
  value={formData.code}
  onChange={(e) => setFormData({ ...formData, code: e.target.value })}
  maxLength={4}
/>
```

#### Table

```typescript
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

<Table>
  <TableHeader>
    <TableRow>
      <TableHead>Code</TableHead>
      <TableHead>Name</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    {organisms.map(org => (
      <TableRow key={org.id}>
        <TableCell>{org.code}</TableCell>
        <TableCell>{org.name}</TableCell>
      </TableRow>
    ))}
  </TableBody>
</Table>
```

#### Toast Notifications

```typescript
import { useToast } from '@/hooks/use-toast'

const { toast } = useToast()

toast({
  title: 'Success',
  description: 'Organism created successfully',
})

toast({
  title: 'Error',
  description: 'Failed to create organism',
  variant: 'destructive',
})
```

### Customizing Components

**You own the code**, so modify freely:

```typescript
// src/components/ui/button.tsx
export function Button({ className, variant, ...props }) {
  return (
    <button
      className={cn(
        "rounded-md px-4 py-2",
        variant === "destructive" && "bg-red-600",
        className
      )}
      {...props}
    />
  )
}
```

**Change colors, sizes, behavior - it's your code!**

---

## Summary: Key Takeaways

### TypeScript
- Use `interface` for objects, `type` for unions
- `?` makes fields optional
- `|` creates union types
- `<T>` creates generic (reusable) types
- `as` tells TypeScript "trust me on the type"

### Vite
- Entry point: `main.tsx` (not `index.js`)
- Env vars: `import.meta.env.VITE_X` (not `process.env`)
- 30x faster than Create React App
- ES modules, not CommonJS

### Modern React (2024)
- **Server state:** React Query (not useState + useEffect)
- **Client state:** useState
- **Routing:** React Router v6 (`element` prop)
- **Error handling:** Error boundaries

### React Query
- `useQuery` for reading data (GET)
- `useMutation` for changing data (POST/PUT/DELETE)
- Automatic caching with `staleTime` and `gcTime`
- Invalidate queries after mutations

### TailwindCSS
- Utility-first: `className="bg-white p-4 rounded-lg"`
- No custom CSS classes
- Responsive: `md:text-lg` (only on medium screens)
- Hover states: `hover:bg-blue-600`

### Shadcn UI
- Copy-paste components (you own the code)
- Built on Radix UI (accessible)
- Styled with TailwindCSS
- Modify freely

---

## Further Reading

- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)
- [Vite Documentation](https://vitejs.dev/guide/)
- [React Query Documentation](https://tanstack.com/query/latest/docs/framework/react/overview)
- [TailwindCSS Documentation](https://tailwindcss.com/docs)
- [Shadcn UI Documentation](https://ui.shadcn.com/)
- [React Router v6 Documentation](https://reactrouter.com/en/main)

---

**Next:** See `ARCHITECTURE.md` for project structure and `README.md` for setup instructions.
