You are a senior frontend architect and React expert.

Your task is to design a **clean, scalable, production-grade frontend architecture** for a stock analysis and portfolio management system.

This is NOT a simple UI task. Focus on:
- clean design
- modularity
- long-term maintainability
- consistent UX
- extensibility

---

# 1. Project Context

The system includes:
- stock recommendation engine
- technical analysis visualization
- news + sentiment display
- LLM-generated reports
- portfolio tracking (via broker API like Kite Connect)

The UI should allow:
- browsing stocks
- viewing detailed analysis
- managing portfolio
- running recommendation pipeline
- chatting with the system (LLM chat interface)

---

# 2. Tech Stack Requirements (STRICT)

Use only modern, standard, widely adopted tools:

### Core
- React 18+ (with functional components)
- TypeScript (strict mode)
- Vite (SPA — no SSR; local personal app)
- React Router v6 (client-side routing)

### UI System
- shadcn/ui (MANDATORY)
- Tailwind CSS
- Lucide icons

### State Management
- React Query (server state)
- Zustand or Context (client state)

### Charts
- TradingView lightweight charts OR Recharts

### Forms
- React Hook Form + Zod validation

### Chat
- Use a standard chat UI library (e.g. `ai/react`, `react-chat-ui`, or similar)
- Should support streaming responses

---

# 3. Design Principles

You MUST follow:

## 3.1 Clean Architecture (Frontend)
- Separate:
  - UI components
  - business logic
  - API layer
- No direct API calls inside UI components

## 3.2 Component Design
- Small, reusable, composable components
- No monolithic pages
- Use composition over inheritance

## 3.3 Consistent UI/UX
- Use shadcn components everywhere
- Centralized theme
- Consistent spacing, typography, colors

## 3.4 Data Contracts
- Strong typing for all API responses
- Shared types across app

## 3.5 Scalability
- Feature-based folder structure
- Easy to add new modules (e.g., options trading later)

---

# 4. Required Features (Break into modules)

## 4.1 Dashboard
- Top recommendations (Top 3 stocks)
- Summary cards
- Market overview

## 4.2 Stock Detail Page
- Price chart (interactive)
- Technical indicators
- News + sentiment
- LLM-generated report

## 4.3 Portfolio Page
- Holdings
- Allocation visualization
- Risk metrics

## 4.4 Recommendation Engine UI
- Trigger pipeline
- Show ranked stocks with scores

## 4.5 Chat Interface
- Chat with system about stocks
- Show structured responses
- Streaming support
- Context-aware (selected stock)

---

# 5. Folder Structure (MANDATORY)

Design a clean structure like:

```
    /src
      /routes            (React Router route components: Dashboard, StockDetail, Portfolio, Chat, Recommendations, Settings)
      /router.tsx        (route definitions)
      /main.tsx          (entry point: providers tree + <RouterProvider/>)

      /components
        /ui              (shadcn base components)
        /shared          (PageHeader, EmptyState, ErrorState, Skeletons)
        /layout          (AppShell, Sidebar, TopBar)
        /charts
        /stock
        /portfolio

      /features
        /stocks
        /portfolio
        /recommendation
        /news
        /report
        /chat

      /lib
        /api             (API client + endpoints)
        /hooks           (generic custom hooks)
        /utils
        /types           (mirrors src/contracts/*.py)

      /store             (Zustand stores)
      /styles            (globals.css, Tailwind tokens)
```

Explain WHY each folder exists.

---

# 6. API Integration Layer

Design:
- centralized API client
- hooks like:
  - useStocks()
  - useStock(symbol)
  - useRecommendations()
  - usePortfolio()

Use React Query properly:
- caching
- invalidation
- background refresh

---

# 7. UI/UX System (IMPORTANT)

Define:
- spacing scale
- typography scale
- color system (light/dark mode)
- card layouts
- loading states (skeletons)
- error states

Use shadcn components like:
- Card
- Tabs
- Dialog
- Table
- Button

---

# 8. Chat System Design

Explain:
- how chat state is managed
- how streaming responses are handled
- how context (selected stock) is injected
- UI structure for chat panel

---

# 9. Performance Considerations

- code splitting
- lazy loading charts
- memoization
- avoiding unnecessary re-renders

---

# 10. Deliverables

Provide:

1. Full architecture explanation
2. Folder structure with reasoning
3. Key component hierarchy
4. Example of:
   - API hook
   - page composition
5. Chat integration design
6. UI system definition

DO NOT:
- dump large code blocks
- skip reasoning
- give generic answers

Focus on **engineering clarity + system design quality**
