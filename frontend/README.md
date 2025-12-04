# KEGG Explore - React Frontend

Modern React + TypeScript frontend for KEGG gene ortholog discovery and analysis.

Built with:
- **React 18.3.1** - UI library
- **TypeScript 5.6.2** - Type safety
- **Vite 5.4.10** - Build tool (30x faster than CRA)
- **React Query** - Server state management
- **TailwindCSS** - Utility-first styling
- **Shadcn UI** - Accessible component library

---

## Quick Start

### Prerequisites

**Required:**
- Node.js **24.11.1** (see [Node Version Management](#node-version-management))
- npm (comes with Node.js)
- Backend API running at `http://localhost:8000` (see [Backend Setup](#backend-setup))

**Optional:**
- nvm (Node Version Manager) - Recommended for managing Node versions

### Installation

```bash
# Navigate to frontend directory
cd /Users/gladiator/Projects/kgene-v1/frontend

# Install dependencies
npm install
```

### Development

```bash
# Start development server
npm run dev

# Open in browser
# http://localhost:5173
```

**That's it!** The app should now be running and connected to your backend.

---

## Node Version Management

This project requires **Node.js 24.11.1** (specified in `.nvmrc`).

### With nvm (Recommended)

```bash
# Install the required version
nvm install 24.11.1

# Use it for this project
nvm use

# Verify
node --version  # Should show v24.11.1
```

### Without nvm

Download Node.js 24.11.1 from [nodejs.org](https://nodejs.org/) and install manually.

**See `NODE_VERSION.md` for detailed explanation of how `.nvmrc` works in different environments.**

---

## Available Scripts

### `npm run dev`

Starts the development server with Hot Module Replacement (HMR).

- **URL:** http://localhost:5173
- **Changes:** Reflected instantly (< 100ms)
- **Port:** 5173 (Vite default)

**Output:**
```
VITE v5.4.10  ready in 500 ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
➜  press h + enter to show help
```

### `npm run build`

Builds the app for production.

- **Output:** `dist/` directory
- **Optimized:** Minified, tree-shaken, bundled
- **Assets:** Static files ready for deployment

**Output:**
```
vite v5.4.10 building for production...
✓ 335 modules transformed.
dist/index.html                  0.46 kB
dist/assets/index-a1b2c3d4.js  109.06 kB │ gzip: 35.82 kB
✓ built in 1.14s
```

### `npm run preview`

Preview production build locally.

- **URL:** http://localhost:4173
- **Tests:** Production build before deployment

```bash
npm run build
npm run preview
```

### `npm run lint`

Runs ESLint to check code quality.

```bash
npm run lint
```

**Checks:**
- TypeScript errors
- React best practices
- Code style issues

### `npm test`

Runs tests with Vitest.

```bash
npm test        # Run all tests
npm test:watch  # Watch mode
npm test:ui     # UI mode (if configured)
```

**Current status:** Test suite is set up but no tests written yet (future work).

---

## Backend Setup

The frontend requires the FastAPI backend to be running.

### Option 1: Docker (Easiest)

```bash
# From project root
cd /Users/gladiator/Projects/kgene-v1
docker-compose up backend

# Backend will be available at:
# http://localhost:8000
```

### Option 2: Local Python

```bash
# From backend directory
cd /Users/gladiator/Projects/kgene-v1/backend
python -m uvicorn app.main:app --reload

# Backend will be available at:
# http://localhost:8000
```

### Verify Backend is Running

Open http://localhost:8000/docs in your browser. You should see the FastAPI Swagger documentation.

---

## Project Structure

```
frontend/
├── public/              # Static assets
│   └── vite.svg
│
├── src/
│   ├── components/     # Reusable UI components
│   │   └── ui/        # Shadcn UI components
│   │
│   ├── config/        # App configuration
│   │   └── queryClient.ts  # React Query config
│   │
│   ├── lib/           # Core logic
│   │   ├── api/       # API client and endpoints
│   │   │   ├── client.ts     # Axios with interceptors
│   │   │   └── organisms.ts  # Organism API methods
│   │   │
│   │   └── hooks/     # Custom React hooks
│   │       ├── useOrganisms.ts
│   │       ├── useCreateOrganism.ts
│   │       └── useDeleteOrganism.ts
│   │
│   ├── pages/         # Page components (routes)
│   │   └── Dashboard.tsx
│   │
│   ├── types/         # TypeScript definitions
│   │   ├── organism.ts
│   │   ├── error.ts
│   │   └── index.ts
│   │
│   ├── App.tsx        # Root component
│   ├── main.tsx       # Entry point
│   └── index.css      # Global styles
│
├── docs/              # Documentation
│   ├── LEARNING.md    # TypeScript/Vite/React guide
│   └── ARCHITECTURE.md # Project structure guide
│
├── .env.development   # Environment variables
├── package.json       # Dependencies
├── vite.config.ts     # Vite configuration
└── tailwind.config.js # TailwindCSS configuration
```

**See `docs/ARCHITECTURE.md` for detailed explanation of each directory.**

---

## Environment Variables

Environment variables are configured in `.env.development`:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

**Important:**
- Vite requires `VITE_` prefix (different from Create React App's `REACT_APP_`)
- Access in code: `import.meta.env.VITE_API_BASE_URL`
- Changes require dev server restart

### Adding New Variables

1. Add to `.env.development`:
   ```bash
   VITE_MY_VARIABLE=value
   ```

2. Access in code:
   ```typescript
   const myVar = import.meta.env.VITE_MY_VARIABLE
   ```

3. Restart dev server:
   ```bash
   # Stop server (Ctrl+C)
   npm run dev
   ```

---

## Features

### Current Features (MVP)

- ✅ **Organism Management**
  - View list of organisms
  - Create new organisms (with validation)
  - Delete organisms (with confirmation)
  - Real-time data updates

- ✅ **Form Validation**
  - Organism code: 3-4 lowercase letters
  - Duplicate detection
  - User-friendly error messages

- ✅ **Error Handling**
  - Correlation ID tracking
  - Toast notifications
  - Error boundaries

- ✅ **Loading States**
  - Skeleton screens
  - Loading spinners
  - Disabled buttons during mutations

### Future Features

- 🔄 **Organism Detail Page**
  - View single organism
  - Gene count statistics
  - Start processing jobs

- 🔄 **Gene Browser**
  - Advanced filtering (has ortholog, identity %, species)
  - Sortable columns
  - Pagination
  - CSV export

- 🔄 **Process Monitor**
  - Real-time job progress
  - Error tracking
  - Retry failed jobs

---

## API Integration

### Backend API

- **Base URL:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

### Key Endpoints

**Organisms:**
- `GET /api/organisms` - List organisms
- `POST /api/organisms` - Create organism
- `DELETE /api/organisms/{id}` - Delete organism

### Request Flow

```
Component
    ↓
Custom Hook (useOrganisms)
    ↓
API Method (getOrganisms)
    ↓
Axios Client (with interceptors)
    ↓
Backend API (FastAPI)
```

**See `docs/ARCHITECTURE.md` for detailed data flow diagrams.**

---

## TypeScript

This project uses TypeScript for type safety.

### Key Concepts

**Interfaces:**
```typescript
interface Organism {
  id: number
  code: string
  name: string
  status?: "pending" | "complete" | "error"
}
```

**Type Assertions:**
```typescript
const error = err as ApiError
```

**Generics:**
```typescript
const { data } = await apiClient.get<Organism[]>('/organisms')
```

**See `docs/LEARNING.md` for comprehensive TypeScript guide.**

---

## Styling

### TailwindCSS

Utility-first CSS framework. Style directly in JSX:

```typescript
<div className="bg-white rounded-lg p-4 shadow">
  Content
</div>
```

**Common patterns:**
- Layout: `flex items-center justify-between`
- Spacing: `p-4` (padding), `m-4` (margin), `space-y-4` (vertical gaps)
- Colors: `bg-primary-500`, `text-gray-700`
- Responsive: `text-sm md:text-base lg:text-lg`

### Custom Colors

See `tailwind.config.js`:

```javascript
colors: {
  primary: {
    50: '#eff6ff',   // Lightest blue
    500: '#3b82f6',  // Main blue
    900: '#1e3a8a',  // Darkest blue
  },
}
```

**Usage:**
```typescript
<Button className="bg-primary-500 hover:bg-primary-600">
  Click me
</Button>
```

### Shadcn UI Components

Pre-built accessible components. Copy-paste into your codebase:

```bash
# Add new component
npx shadcn@latest add select

# Components are added to:
src/components/ui/select.tsx
```

**See `docs/LEARNING.md` for component usage guide.**

---

## React Query

Modern data fetching library that replaces `useState` + `useEffect`.

### Query (Read Data)

```typescript
const { data, isLoading, error } = useOrganisms()
```

**Features:**
- Automatic caching
- Background refetching
- Deduplication

### Mutation (Change Data)

```typescript
const createMutation = useCreateOrganism()

await createMutation.mutateAsync({
  code: 'eco',
  name: 'E. coli'
})
```

**Features:**
- Loading states
- Error handling
- Cache invalidation

### DevTools

React Query DevTools in bottom-left corner:
- View all queries
- See cached data
- Manually refetch

**See `docs/LEARNING.md` for React Query deep dive.**

---

## Troubleshooting

### Port 5173 already in use

**Error:**
```
Port 5173 is in use, trying another one...
```

**Solutions:**

1. **Stop other Vite processes:**
   ```bash
   lsof -i :5173
   kill -9 <PID>
   ```

2. **Use different port:**
   ```bash
   npm run dev -- --port 3000
   ```

### Cannot connect to backend

**Error in browser console:**
```
Network Error: Failed to fetch
```

**Solutions:**

1. **Check backend is running:**
   ```bash
   curl http://localhost:8000/api/organisms
   ```

2. **Verify environment variable:**
   ```bash
   # Check .env.development
   cat .env.development
   # Should show: VITE_API_BASE_URL=http://localhost:8000
   ```

3. **Restart dev server:**
   ```bash
   # Ctrl+C to stop
   npm run dev
   ```

### TypeScript errors

**Error:**
```
TS2307: Cannot find module '@/types'
```

**Solutions:**

1. **Check path aliases in `tsconfig.json`:**
   ```json
   {
     "compilerOptions": {
       "baseUrl": ".",
       "paths": {
         "@/*": ["./src/*"]
       }
     }
   }
   ```

2. **Restart TypeScript server in VS Code:**
   - `Cmd + Shift + P` (Mac) or `Ctrl + Shift + P` (Windows/Linux)
   - Type: "TypeScript: Restart TS Server"

### Build fails

**Error:**
```
Build failed with 1 error
```

**Solutions:**

1. **Check TypeScript errors:**
   ```bash
   npm run tsc
   ```

2. **Clear node_modules and reinstall:**
   ```bash
   rm -rf node_modules package-lock.json
   npm install
   ```

3. **Check for syntax errors:**
   ```bash
   npm run lint
   ```

### Hot reload not working

**Issue:** File changes don't reflect in browser.

**Solutions:**

1. **Restart dev server:**
   ```bash
   # Ctrl+C to stop
   npm run dev
   ```

2. **Hard refresh browser:**
   - Mac: `Cmd + Shift + R`
   - Windows/Linux: `Ctrl + Shift + R`

3. **Check file watcher limits (Linux):**
   ```bash
   echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
   sudo sysctl -p
   ```

---

## Testing

Test suite is configured with Vitest but no tests written yet.

### Running Tests

```bash
npm test        # Run once
npm test:watch  # Watch mode
```

### Writing Tests

**Example test:**

```typescript
// src/lib/hooks/__tests__/useOrganisms.test.ts
import { renderHook, waitFor } from '@testing-library/react'
import { useOrganisms } from '../useOrganisms'

describe('useOrganisms', () => {
  it('fetches organisms successfully', async () => {
    const { result } = renderHook(() => useOrganisms())

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toHaveLength(3)
  })
})
```

**Future work:** Add comprehensive test coverage.

---

## Deployment

### Build for Production

```bash
npm run build
```

**Output:** `dist/` directory with optimized static files.

### Deploy to Netlify

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Deploy
netlify deploy --prod --dir=dist
```

**Settings:**
- Build command: `npm run build`
- Publish directory: `dist`

### Deploy to Vercel

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel --prod
```

**Settings:**
- Framework Preset: Vite
- Build command: `npm run build`
- Output directory: `dist`

### Environment Variables

Set in deployment platform:
```
VITE_API_BASE_URL=https://your-backend-api.com
```

---

## Learning Resources

### Documentation

- **[LEARNING.md](docs/LEARNING.md)** - TypeScript, Vite, and modern React guide
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Project structure and patterns
- **[NODE_VERSION.md](NODE_VERSION.md)** - Node version management guide

### External Resources

- [React Documentation](https://react.dev/) - Official React docs
- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)
- [Vite Guide](https://vitejs.dev/guide/)
- [React Query Docs](https://tanstack.com/query/latest/docs/framework/react/overview)
- [TailwindCSS Docs](https://tailwindcss.com/docs)
- [Shadcn UI](https://ui.shadcn.com/)

---

## Contributing

### Code Style

- **TypeScript:** Strict mode enabled
- **Linting:** ESLint with React rules
- **Formatting:** Prettier (if configured)

### Commit Guidelines

```bash
# Good commit messages
git commit -m "feat: Add organism filtering"
git commit -m "fix: Fix correlation ID tracking"
git commit -m "docs: Update README with deployment guide"
```

### Pull Requests

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes and commit
3. Push: `git push origin feature/my-feature`
4. Create pull request on GitHub

---

## Tech Stack Details

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.3.1 | UI library |
| TypeScript | 5.6.2 | Type safety |
| Vite | 5.4.10 | Build tool |
| React Router | 6.28.0 | Client-side routing |
| React Query | 5.62.12 | Server state management |
| Axios | 1.7.9 | HTTP client |
| TailwindCSS | 3.4.18 | Utility-first CSS |
| Shadcn UI | Latest | Component library |
| Lucide React | 0.469.0 | Icon library |
| Vitest | 2.1.8 | Test framework |

**See `package.json` for full dependency list.**

---

## License

[Add your license here]

---

## Support

For questions or issues:

1. Check [LEARNING.md](docs/LEARNING.md) for concept explanations
2. Check [ARCHITECTURE.md](docs/ARCHITECTURE.md) for structure details
3. Check [Troubleshooting](#troubleshooting) section above
4. Search existing issues on GitHub
5. Create new issue with:
   - Error message
   - Steps to reproduce
   - Environment (Node version, OS)
   - Screenshots if applicable

---

**Built with ❤️ for bioinformatics research**
