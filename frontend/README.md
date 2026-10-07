# Frontend

Next.js 16 (App Router) · TypeScript · Tailwind CSS 4 web interface for the
**Student Academic Analytics and Risk Prediction System**.

```
src/
├── app/                 # Routes: one folder per module, plus layout and design tokens
├── components/
│   ├── layout/          # App shell, navigation, page header, brand
│   ├── status/          # Live backend status
│   ├── theme/           # Light / dark / system appearance
│   └── ui/              # Design-system primitives (grouped lists, sections, badges)
└── lib/                 # Module registry, API client, site metadata
```

## Design system

Tokens live in `src/app/globals.css` and are exposed as Tailwind utilities
(`bg-surface`, `text-text-secondary`, `divide-separator`, `bg-accent-soft`, …).
Every colour has a light and a dark value; the theme follows the system unless the
user picks one explicitly, which is applied before first paint to avoid flashing.

Guidelines: neutral surfaces with a single accent colour, hairline separators instead
of heavy borders, grouped lists rather than card grids, system typography with tight
display tracking, and no figures that are not returned by the API.

## Setup

```bash
npm install
cp .env.example .env.local   # optional; defaults to http://localhost:8000/api/v1
npm run dev                  # http://localhost:3000
```

## Scripts

| Script              | Purpose                                   |
| ------------------- | ----------------------------------------- |
| `npm run dev`       | Development server                        |
| `npm run build`     | Production build                          |
| `npm run lint`      | ESLint (Next.js core-web-vitals + TS)     |
| `npm run typecheck` | Route type generation + `tsc --noEmit`    |
| `npm test`          | Vitest + Testing Library                  |
| `npm run format`    | Prettier (with Tailwind class sorting)    |
