# VIDYA-PATH

A tuition-center management web app for teachers, students, and parents.

## Current state

- Next.js App Router foundation and responsive landing page
- Interactive role switcher and sign-in modal (authentication is intentionally not active yet)
- Preserved the original Python + SQLite attendance prototype in `app.py`
- Supabase environment variable template at `.env.example`

## Run locally

```bash
npm install
npm run dev
```

Open http://localhost:3000.

## Supabase setup

Create a Supabase project and add these variables to your local `.env.local` and to Vercel Project Settings:

```env
NEXT_PUBLIC_SUPABASE_URL=your-project-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

Do not expose a service-role key in browser code. Authentication and role-protected dashboards must be added before using real student or parent information.

## Deploy

Vercel should detect Next.js from `package.json`. Use the repository root as the Root Directory. The Python prototype is not the deployed web entry point.

## Prototype (legacy)

The original standard-library Python prototype remains available separately:

```bash
python app.py seed
python app.py
python -m unittest -v
```

It is not a production deployment and should use fictional demo data only.
