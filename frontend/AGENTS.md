# SkyAnalyst — Agent Guidelines & Architecture Rules

## Tech Stack
- **Framework**: React 18 + Vite + TypeScript (Strict Mode)
- **Styling**: Tailwind CSS + Custom Glassmorphism System
- **UI Primitives**: Radix UI / shadcn-style component primitives (Button, Card, Tabs, Table, Sheet, Dialog, DropdownMenu, Tooltip, Avatar, Badge, Skeleton, Sonner)
- **Routing**: React Router v6
- **Animations**: Framer Motion (deliberate, defense-grade, Apple/Linear aesthetic)
- **Data Visualizations**: Recharts (NDVI time series, dual-axis telemetry, area masks)
- **Data Fetching & Cache**: TanStack Query (React Query v5)
- **Icons**: Lucide React
- **Notifications**: Sonner (Toast system)

## Coding Conventions
1. **TypeScript Strict Mode**: Zero `any` types. All API responses, state, and component props must be strictly typed using interfaces defined in `src/types/`.
2. **Functional Components & Named Exports**: All React components must be functional components exported with explicit named exports (e.g., `export const GlassPanel: React.FC<...> = ...`).
3. **File Structure**:
   - Pages: `src/pages/`
   - Reusable UI & Domain Components: `src/components/`
   - TanStack Query Hooks: `src/hooks/`
   - Data Models & Types: `src/types/`
   - Utilities & API Client: `src/lib/`
   - Shell & Navigation Layouts: `src/layouts/`
4. **Mandatory UI States**:
   - **Loading States**: Shimmer skeletons (`SkeletonCard`, `SkeletonTable`) that match the exact geometry of the loaded layout to eliminate layout shift. Never use generic full-page spinners.
   - **Error States**: Dedicated `ErrorCard` with human-readable error descriptions and a "Retry" button linked to query refetch. Never crash or render blank screens.
   - **Empty States**: Centered Lucide icon in subtle glass container with title, explanatory text, and an actionable CTA button.
5. **API Fetching Rule**:
   - All backend communication MUST go through TanStack Query hooks in `src/hooks/`.
   - Never call `fetch()` or `axios` directly inside page or layout components.
   - All network calls must pass through `src/lib/api.ts`, which reads `import.meta.env.VITE_API_BASE_URL`. Never hardcode `http://localhost:8000`.
6. **Styling Rule**:
   - Use Tailwind CSS utility classes and design tokens exclusively. No inline styles (except dynamic position geometry like tile overlay coordinates).
