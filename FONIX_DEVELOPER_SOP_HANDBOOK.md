# Fonix Employee Developer SOP Handbook
*Standard Operating Procedures — Synthesised from 87 SOPs*
*Every developer reads this. No exceptions.*
*Version 1.0 · April 2026 · 15 Sections · 87 SOPs*

---

## 📌 SOP Severity Levels
*   **P1 — Critical:** Non-negotiable. Violating this SOP causes real damage — broken code, data loss, production incidents.
*   **P2 — Important:** Required for professional-grade work. Not following causes rework, inconsistency, and technical debt.
*   **P3 — Reference:** Deep knowledge for specific scenarios. Read when the situation applies to your current project.

---

## 👥 Who Must Read What
Reading this handbook is not optional. It is a job requirement, same as showing up.

| Role | Minimum Required Reading | By When |
| :--- | :--- | :--- |
| **Intern / Trainee** | Chapters 1–3 fully before writing any code | First week |
| **Junior Developer** | All P1 SOPs. Full handbook read-through. | First two weeks |
| **Mid-Level Developer** | All P1 and P2 SOPs. P3 SOPs for your current project. | First week |
| **Senior Developer** | All SOPs. You enforce these on others. | Day one |
| **Team Lead / CTO** | All SOPs. You own and maintain this document. | Day one |
| **QA Engineer** | Chapters 1, 2, and Chapter 6 (Testing) fully. | First week |

### How to use this handbook
*   When you are about to write code, ask: *"Is there an SOP for this?"* If yes, follow it.
*   When you receive a task, check the relevant chapter for the standards that apply.
*   When you review a PR, use the standards in Chapter 3 as your baseline.
*   When this document conflicts with your intuition — **the SOP wins.** Raise the disagreement in retro, not in the PR.

---

## 📂 CHAPTER 1: Foundations
*What Every Developer Must Know Before Writing a Single Line of Code*

These SOPs are not about syntax or frameworks. They are the mental models that make everything else make sense. A developer who skips Section A will make mistakes that no linter or code review can catch.

### 1.1 How the Web Works [A-01 · P1 · Everyone]
Every single thing Fonix builds runs on the web. A developer who does not understand how the web works will write code that works sometimes and breaks in mysterious ways — and will not understand why.

#### The request journey — 5 steps
1.  Browser asks DNS to translate the domain name into an IP address.
2.  Browser opens a TCP connection to that IP on port 443 (HTTPS) or 80 (HTTP).
3.  Browser sends an HTTP request: method, path, headers, and optional body.
4.  Server processes the request and sends back an HTTP response: status code, headers, and body.
5.  Browser renders HTML, runs JavaScript, or passes JSON data to your code.

#### HTTP methods — use the correct verb
| Method | Use for | Never use for |
| :--- | :--- | :--- |
| **GET** | Reading data. Must never change anything server-side. | Creating or modifying resources |
| **POST** | Creating a new resource. | Reading data |
| **PUT** | Completely replacing an existing resource. | Partial updates |
| **PATCH** | Partially updating an existing resource. | Full replacement |
| **DELETE** | Removing a resource. | Anything other than deletion |

#### HTTP status codes — know these without looking them up
| Code | Meaning | Use it when |
| :--- | :--- | :--- |
| **200** | OK | Successful GET, PUT, PATCH — data returned |
| **201** | Created | Successful POST — a new resource was created |
| **204** | No Content | Successful DELETE — nothing to return |
| **400** | Bad Request | Client sent invalid data — validation failed |
| **401** | Unauthorized | Not authenticated — must log in first |
| **403** | Forbidden | Authenticated but not authorised for this action |
| **404** | Not Found | Resource does not exist |
| **409** | Conflict | Duplicate resource or state conflict |
| **422** | Unprocessable | Data format valid but fails business rules |
| **500** | Server Error | Something broke server-side — investigate immediately |

---

### 1.2 REST APIs [A-02 · P1 · Everyone]
REST is a set of conventions that makes APIs predictable. Every developer can understand any Fonix API without being told how it works — because they all follow the same pattern.

#### Core mental model: URLs are nouns, methods are verbs
*   **DO:**
    *   `GET /api/v1/projects`
    *   `POST /api/v1/projects`
    *   `DELETE /api/v1/projects/123`
    *   `GET /api/v1/projects/123/tasks`
*   **DON'T:**
    *   `GET /api/getProjects` (verb in URL)
    *   `POST /api/deleteProject` (wrong method)
    *   `/api/project_list` (inconsistent naming)
    *   `POST /api/projects/123/getTasksForProject`

#### Standard response envelope — every Fonix API returns this shape
```json
// Success — single resource:
{ 
  "success": true, 
  "data": { "id": "abc-123", "name": "E-Commerce App" } 
}

// Success — list with pagination:
{ 
  "success": true, 
  "data": [...], 
  "pagination": { "page": 1, "limit": 20, "total": 143 } 
}

// Error:
{ 
  "success": false, 
  "error": { "code": "NOT_FOUND", "message": "Project not found" } 
}
```

---

### 1.3 Authentication [A-03 · P1 · Everyone]
Authentication is the most security-sensitive part of any application. Every developer — including interns — must understand how it works because every developer writes code that touches it.

#### Authentication vs Authorisation
*   **Authentication:** Proving who you are. (e.g., Logging in with email and password).
*   **Authorisation:** Proving you are allowed to do something. (e.g., Checking you have the admin role before deleting a user).

#### JWT flow at Fonix — step by step
1.  User submits email + password to `POST /api/v1/auth/login`.
2.  Server validates — compares the password hash, never the plain-text password.
3.  Server issues: `access token` (15-min lifetime) + `refresh token` (7-day lifetime).
4.  Access token → response body. Refresh token → HttpOnly cookie.
5.  Every API request includes the access token in the `Authorization` header.
6.  When access token expires, client silently exchanges the refresh token for a new one.

#### Token storage — non-negotiable
*   **Web:** Access token in memory (Zustand / React state). Refresh token in HttpOnly cookie.
*   **Mobile:** Access token in memory. Refresh token in `expo-secure-store`.
*   **CRITICAL:** NEVER store tokens in `localStorage` — readable by any JavaScript, vulnerable to XSS.
*   **CRITICAL:** NEVER put JWT secrets, database passwords, or API keys in frontend code.

---

### 1.4 Naming Things [A-06 · P1 · Everyone]
Code is read far more than it is written. A feature you write in two days will be debugged for two years. The single biggest factor determining how long maintenance takes is how well everything is named.

#### Casing conventions
*   `camelCase`: `getUserById`, `projectCount` — Variables, functions, methods (JS/TS)
*   `PascalCase`: `ProjectCard`, `UserProfile` — React components, TypeScript types/interfaces, classes
*   `SCREAMING_SNAKE`: `MAX_RETRY_ATTEMPTS` — Constants, environment variables
*   `kebab-case`: `user-profile.tsx` — File names, CSS classes, URL slugs
*   `snake_case`: `user_id`, `created_at` — Database columns, Python variables and functions

#### Rules
*   Name variables by what they contain: `userProjects` not `result` or `data`
*   Name functions with a verb: `getUserById()`, `validateEmailFormat()`, `formatCurrencyINR()`
*   Booleans start with `is`, `has`, `can`, `should`: `isAuthenticated`, `hasPermission`
*   Forbidden names — never use: `data`, `result`, `temp`, `info`, `val`, `obj`, `x`, `d`
*   Database tables: plural `snake_case` — `projects`, `user_push_tokens`. Columns: `snake_case` — `created_at`, `tenant_id`

---

### 1.5 Environment Variables [A-07 · P1 · Everyone]
Every year, developers accidentally publish API keys to GitHub. Attackers find them within minutes using automated scanners. This has happened to banks, government agencies, and well-funded startups. It must not happen at Fonix.

#### These must NEVER appear in source code
*   Database connection strings (`DATABASE_URL`)
*   API keys: Stripe, Razorpay, Anthropic, Resend, Twilio, AWS
*   JWT secrets and signing keys (`JWT_SECRET`)
*   Any password, private key, or access token
*   URLs with credentials embedded in them

#### The .env pattern
*   `.env.example` — committed to git (keys only, no real values)
    ```ini
    DATABASE_URL=postgresql://user:password@localhost:5432/mydb
    JWT_SECRET=your-secret-key-minimum-32-characters
    ANTHROPIC_API_KEY=
    RESEND_API_KEY=
    ```
*   `.env` — NOT committed to git (real values, always in `.gitignore`)
    ```ini
    DATABASE_URL=postgresql://fonix_prod:realpassword@prod.db.fonix.in:5432/fonix
    JWT_SECRET=j8K2mN9pQ3rT6vX1yZ4aB7cD0eF5gH8jK3
    ```

#### If you accidentally commit a secret:
1.  Immediately rotate the key — change it at the provider (Stripe, AWS, etc).
2.  Remove it from code and ensure `.gitignore` is correct.
3.  Do **NOT** just delete the commit — git history is permanent.
4.  Tell the CTO immediately. A committed secret is treated as fully compromised.

---

### 1.6 Git and Version Control [A-08 · P1 · Everyone]
Git is the one tool every Fonix developer uses every single day. Used well, it is your safety net. Used badly, it destroys work and creates security breaches.

#### Branching strategy
| Branch Type | Format | Merges Into | Example |
| :--- | :--- | :--- | :--- |
| **main** | Protected. Production only. Every merge deploys to production. | — | `main` |
| **develop** | Protected. Staging only. Every merge deploys to staging. | — | `develop` |
| **Feature** | `feature/FON-[ticket]-[description]` | `develop` | `feature/FON-201-user-auth` |
| **Bug Fix** | `fix/FON-[ticket]-[description]` | `develop` | `fix/FON-308-payment-timeout` |
| **Hotfix** | `hotfix/FON-[ticket]-[description]` | `main` + `develop` | `hotfix/FON-412-null-crash` |
| **Chore** | `chore/[description]` | `develop` | `chore/upgrade-prisma-v5-11` |

#### Commit message format — Conventional Commits
Format: `type(scope): short description in present tense`
Types: `feat`, `fix`, `chore`, `refactor`, `docs`, `test`, `perf`, `ci`

*   **CORRECT:**
    *   `feat(auth): add JWT refresh token rotation`
    *   `fix(projects): resolve N+1 query in project list endpoint`
    *   `chore: upgrade Prisma from v5.8 to v5.11`
*   **INCORRECT:**
    *   `fixed bug`
    *   `WIP`
    *   `update files`

#### What must NEVER be committed to git
*   `.env` files (any environment)
*   `node_modules/` or `__pycache__/` or `.venv/`
*   API keys, tokens, passwords, or connection strings in code
*   Build artifacts: `.next/`, `dist/`, `build/`
*   Database dumps with real user data
*   SSL certificates, private keys, `.pem` files

---

### 1.7 Common Beginner Mistakes [A-09 · P1 · Everyone]
Every mistake below has been made on real projects at agencies like Fonix. Some cost hours. Some caused production incidents.

#### JavaScript / TypeScript
*   Using `var`. Always use `const` by default, `let` only when the value must be reassigned. `var` is obsolete.
*   Not using optional chaining on nullable values. `user.profile.name` crashes if user is null. Use `user?.profile?.name`.
*   Using `==` instead of `===`. Always use strict equality.
*   Mutating React state directly: `state.items.push(x)`. Use `setItems([...items, x])`.
*   Adding `@ts-ignore` to silence TypeScript errors. Fix the type error properly.

#### Git and process
*   Committing to `main` or `develop` directly. All work goes through a feature branch and PR.
*   Committing `.env` files or `node_modules`. Always check `.gitignore` on first push.
*   Making one enormous commit at the end of a task. Commit small, logical units throughout.
*   Vague commit messages. Write what changed and why.

---

### 1.8 Environments [A-10 · P1 · Everyone]
*"It works on my machine"* is one of the most expensive sentences in software development.

| Feature | Development | Staging | Production |
| :--- | :--- | :--- | :--- |
| **Purpose** | Write and test code | Verify before release | Real users, real money |
| **Branch** | Feature branch | `develop` (auto-deploy on merge) | `main` (manual approval) |
| **Database** | Local / seed data | Anonymised / fake data | Real user data |
| **API Keys** | Sandbox / test keys | Sandbox / test keys | Live keys — real transactions |
| **Access** | Developer only | Team + client UAT | CTO and Team Lead only |

#### The hard rules
1.  Never use live Stripe or Razorpay keys on development or staging.
2.  Never import real production data into development without anonymising it first.
3.  Never SSH into a production server to "quickly fix" something — changes go through CI/CD.
4.  Never grant production server access to junior developers or interns.

---

### 1.9 Technical Debt [A-11 · P1 · Everyone]
Technical debt is the single largest invisible tax on every software project. Every shortcut, every "I'll fix this later" accumulates silently until building new features takes five times longer than it should.

*   When you notice debt: log a ticket immediately — what it is, where it is, what fixing it would require.
*   Do not fix debt without permission. Unplanned refactoring causes its own bugs.
*   Do not create debt without flagging it. If you take a shortcut, create a ticket the same day.
*   **The Boy Scout Rule:** leave the code cleaner than you found it — fix small things in passing, never major refactors without a task.

---

### 1.10 How to Ask for Help [A-12 · P1 · Everyone]

#### The 30-minute rule
If you have been genuinely stuck for 30 minutes — having read the error, searched for it, checked the docs, tried a different approach — **stop and ask.**
*"Genuinely tried"* does not mean staring at the code for 30 minutes. It means actively working through it. If you have not tried yet, try first. Struggling productively is how you learn.

#### A good help request includes:
1.  What you are trying to do (the goal, not just the symptom).
2.  What you have already tried.
3.  The exact error message — paste it, do not paraphrase.
4.  The relevant code snippet — not your entire file.
5.  Your best guess at the cause.

---

## ⚙️ CHAPTER 2: Process & Workflow
*Tasks, Sprints, Standups, Scope Control, Pull Requests, and Communication*

A developer who understands only technical SOPs but not process SOPs will build correct code that solves the wrong problem, miss deadlines by not raising blockers, and create scope creep that nobody planned for.

### 2.1 Task Creation and Acceptance Criteria [B-01 · P1 · Everyone]
A task that is well-written before development starts takes 30 minutes to create and saves 4 hours of rework.

#### The No-Verbal-Task Rule
No development work starts without a written task in Jira/Linear. A verbal instruction from a manager is not a task. Ask them to create a ticket — or create one yourself and have them approve it before you start. If you receive a verbal task and there is no ticket: create it, confirm with the assigner, then start work.

#### Every task must contain:
*   **Title:** One sentence: *"Add pagination to the project list API"* (Required: Yes)
*   **Description:** Why this task exists and what it enables. (Required: Yes)
*   **Acceptance Criteria:** Specific, testable conditions that define done. (Required: Yes)
*   **Figma / design link:** Link to the exact Figma frame. (Required: If UI)
*   **API contract:** Endpoint, request shape, response shape, status codes. (Required: If API)
*   **Edge cases:** Empty state, error state, loading state, permissions. (Required: Yes)
*   **Estimate:** Hours. Honest — not what the deadline needs. (Required: Yes)

#### Good acceptance criteria — Pagination on project list
*   `GET /api/v1/projects` returns 20 items per page by default.
*   Response includes: `{ page, limit, total, totalPages, hasNextPage }`.
*   `?page=2&limit=10` returns the correct slice.
*   `limit > 100` returns 400: *"Limit cannot exceed 100"*.
*   Empty result returns data: `[]` (not null) and `total: 0`.
*   All existing tests pass.

#### A task is done only when ALL of these are true:
*   Code meets every acceptance criterion.
*   Reviewed and approved by at least one other developer.
*   All tests pass and CI/CD pipeline is green.
*   Feature works correctly on the staging environment.
*   QA has signed off (for any user-facing feature).
*   Ticket status updated in Jira/Linear.

---

### 2.2 Sprint Planning and Estimation [B-02 · P1 · Everyone]
Fonix operates on two-week sprints. Work is planned, estimated, committed to, and reviewed every two weeks.

#### The two-week sprint cycle
*   **Monday, Week 1:** Sprint Planning — select and estimate tasks (All developers, 2 hours)
*   **Every day:** Daily Standup — status, blockers, coordination (All developers, 15 minutes)
*   **Friday, Week 1:** Mid-sprint check — are we on track? (Team Lead, 30 minutes)
*   **Friday, Week 2:** Sprint Review — demo completed work (Team + stakeholders, 1 hour)
*   **Friday, Week 2:** Sprint Retrospective — what worked, what did not (Dev team, 45 minutes)
*   **Friday, Week 2:** Backlog Refinement — prepare next sprint (Team Lead + BA, 1 hour)

#### The estimation rule
Estimate for reality, not for what the deadline requires. If a task genuinely takes 8 hours, estimating 4 creates a lie that cascades into missed deadlines, overworked developers, and dropped quality. A bad estimate always costs more than the honest conversation that could have fixed the timeline.

#### When the sprint goes wrong:
1.  Task will take longer than estimated: tell the Team Lead the same day. Do not wait for the sprint review.
2.  You are blocked: raise it in standup the next day. Do not sit on a blocker for more than one day.
3.  Requirements change mid-sprint: do not absorb the change silently. Create a ticket, estimate it, let the Team Lead decide.

---

### 2.3 Daily Standup and Communication [B-03 · P2 · Everyone]
The standup has one job: give the team enough shared context to stay coordinated for the next 24 hours.

#### The three questions — nothing else
*   **What did I complete yesterday?**
    *   *Good answer:* Specific task and outcome: *"Finished pagination endpoint FON-201."*
    *   *Bad answer:* Vague: *"Worked on projects."*
*   **What will I work on today?**
    *   *Good answer:* Specific task: *"Starting project list frontend FON-205."*
    *   *Bad answer:* Open-ended: *"More coding."*
*   **What is blocking me?**
    *   *Good answer:* Specific blocker: *"Waiting for design approval on the modal."*
    *   *Bad answer:* Silence — not raising a blocker.

#### Communication channels — what goes where
*   **Teams:** Quick questions, blockers, status updates. (Response time: Within 2 hours in work hours)
*   **Ticket comments:** Task discussion, decisions, context. (Response time: Within the sprint)
*   **PR comments:** Code review feedback. (Response time: Within 4 hours)
*   **Direct message:** Sensitive or personally urgent matters. (Response time: Within 1 hour)

#### What must always be written — never only verbal
*   Any technical decision: architecture choice, API design, database schema change.
*   Any scope change — even a small one.
*   Any risk or concern about a deadline or quality.
*   *"We agreed in the meeting"* is not documentation. Put the outcome in the ticket.

---

### 2.4 Scope Change Protocol [B-05 · P2 · Team Lead / BA]
Scope creep is the primary reason projects run over budget and over time. At Fonix, scope changes are welcomed — but they must be managed, not absorbed silently.

#### What constitutes scope change
*   Any feature, screen, or functionality not described in the original task or SoW.
*   Changes to a feature that increase the estimated work by more than 20%.
*   New integrations, third-party services, or API requirements not in the original spec.

#### The protocol — four steps
1.  **Stop.** Do not start the out-of-scope work.
2.  **Log it.** Create a new ticket describing the change and your estimate.
3.  **Escalate.** Notify the Team Lead immediately. They notify the client through the correct channel.
4.  **Wait for approval.** Only begin the change once the Team Lead has confirmed it is in scope or approved as a paid change order.

---

### 2.5 Pull Request Process [B-07 · P1 · Everyone]
No code merges without a PR. No PR merges without passing CI checks and an approved code review. This applies to everyone including the CTO.

#### Before opening a PR — author checklist
*   All CI checks pass locally: `npm run lint`, `npm run typecheck`, `npm test`
*   PR targets the correct branch — almost always `develop`, never `main` directly.
*   Branch is up to date with `develop` (rebase or merge before opening).
*   No `console.log` statements. No incomplete `TODO` markers. No commented-out code.
*   New environment variables added to `.env.example` with a comment.

#### PR description template
```markdown
## What this PR does
Brief description and reason.

## How to test
1. Step one to verify it works
2. Edge case to verify

## Checklist
- [ ] Tests written and passing
- [ ] No new lint errors
- [ ] .env.example updated if new vars added

Closes FON-XXX
```

#### What reviewers must check
*   **P1 — Security:** Unsanitised inputs, exposed secrets, broken auth, missing authorisation.
*   **P1 — Correctness:** Edge cases: null, empty array, 0, negative values, unexpected types.
*   **P1 — Data:** Partial writes: are transactions used where multiple tables are written?
*   **P2 — Performance:** N+1 queries, missing indexes, large unnecessary data fetches.
*   **P2 — Errors:** Errors caught and shown to the user meaningfully.
*   **P2 — Tests:** A test that would catch a regression of this change.
*   **P3 — Clarity:** Would another developer understand this code in six months?

---

## 💻 CHAPTER 3: Code Quality & Standards
*TypeScript, Python, CSS, Async/Await, Documentation, and Logging*

Standards exist so any Fonix developer can pick up any Fonix codebase and work in it immediately. Consistency is the point.

### 3.1 JavaScript and TypeScript [F-01 · P1 · JS/TS Developers]

#### Variable declaration rules
*   **DO:**
    *   `const projectId = "abc-123"` // immutable — use const
    *   `let retryCount = 0` // genuinely reassigned later
    *   `const isLoaded = data !== null` // boolean from expression
*   **DON'T:**
    *   `var projectId = "abc-123"` // var is obsolete — never use it
    *   `let MAX_SIZE = 100` // not reassigned — use const
    *   `const x = getData()` // meaningless name

#### TypeScript rules
*   Strict mode required everywhere. `tsconfig.json` must have `"strict": true`.
*   Never use `any`. Use `unknown` for genuinely unknown types, then narrow with type guards.
*   Always annotate return types on exported functions: `function getUser(id: string): Promise<User>`
*   String unions instead of enums: `type Status = "active" | "pending" | "archived"`
*   Never use `@ts-ignore`. Fix the type error properly.

#### Function design
*   One function, one responsibility. If you need "and" to describe it — split it.
*   Maximum 50 lines per function. If longer, extract helpers.
*   Maximum 3 parameters. Use an options object when more are needed.
*   Avoid boolean parameters: `sendEmail(user, true)` is unclear. Use `sendEmail(user, { trackOpens: true })`.

---

### 3.2 How Async/Await Works [F-04 · P1 · Everyone]
Async/await is the standard for handling asynchronous operations at Fonix. Understanding it properly prevents a whole category of bugs.

*   Always use `async/await`. Never mix `.then()` and `await` in the same function.
*   Always wrap async calls in `try/catch`. An unhandled promise rejection crashes silently.
*   Independent async calls run in parallel with `Promise.all()` — not sequentially.

```typescript
// ❌ Sequential — unnecessarily slow:
const user = await getUser(id)
const projects = await getProjects(id) // waits for user needlessly

// ✅ Parallel — both run at the same time:
const [user, projects] = await Promise.all([getUser(id), getProjects(id)])

// ❌ Awaiting inside a loop:
for (const id of ids) { 
  await processItem(id) 
} // sequential N calls

// ✅ Process all at once:
await Promise.all(ids.map(id => processItem(id)))
```

---

### 3.3 Python Standards [F-02 · P1 · Python Developers]
*   All function signatures must have type hints.
*   Format with `black`, lint with `ruff`. Both enforced in CI — failing check blocks the PR.
*   Use Pydantic models for request/response shapes. Never return raw `dict` from API handlers.
*   Use `async def` consistently for FastAPI route handlers.
*   Never build SQL by string concatenation. Always use the ORM or parameterised queries.

---

### 3.4 CSS and Styling Standards [D-02 · P1 · Frontend Developers]

#### The internal-only rule — no exceptions
*   **NEVER:** `@import url("https://fonts.googleapis.com/...")` in any CSS file
*   **NEVER:** `<link href="https://cdn.jsdelivr.net/npm/bootstrap/...">` in any HTML
*   **ALWAYS:** Load fonts via `next/font/google` (build-time, zero runtime CSS)
*   **ALWAYS:** Install icon libraries as npm packages — never CDN
*   *Why:* External stylesheets are render-blocking. If the CDN is slow or down, the UI breaks.

#### Tailwind rules
*   Define brand colours as design tokens in `tailwind.config.ts` — never `bg-[#E8472A]` scattered across 500 files.
*   Use Tailwind variants: `hover:`, `focus:`, `dark:` — never `onMouseEnter` to manipulate inline styles.
*   Inline `style={{}}` only for genuinely dynamic runtime values (e.g. animation progress). Never for colours, padding, or font sizes.
*   Use `lucide-react` for icons (pre-installed). Never load icon fonts from CDN.

---

### 3.5 Documentation and Logging [F-05 · P2 | F-06 · P1 · Backend]

#### Code documentation rules
*   Comment the WHY, not the WHAT. If the code reads like English, it does not need a comment.
*   Write JSDoc / docstrings on all exported functions.
*   Mark workarounds: `// TODO(FON-XXX): remove after migration completes`. Always include the ticket number.

#### Logging standards — use the structured logger, never console.log
*   **Node.js — use Pino:**
    ```typescript
    logger.info({ userId, projectId, action: "project.created" }, "Project created")
    logger.error({ error, userId, path: req.path }, "Failed to process request")
    ```
*   **Python — use loguru:**
    ```python
    logger.info("Project created | project_id={} user_id={}", project_id, user_id)
    ```
*   **NEVER log:** Passwords, JWT tokens, card numbers, full request bodies with PII, AWS credentials.

---

## 📁 CHAPTER 4: Project Structure
*Standard Folder Layouts for Every Stack Fonix Uses*

Every Fonix project uses the same folder layout for its stack. When you open a new project, you know where everything lives. This chapter shows the standard layout for each stack.

### 4.1 React / Next.js App Router [C-01 · P1 · Frontend Developers]
```text
project-root/
├── app/                        # Next.js App Router pages
│   ├── (auth)/                 # Route group — auth pages
│   ├── dashboard/page.tsx      # Server component — thin shell only
│   ├── dashboard/DashboardContent.tsx # Client component — logic here
│   ├── api/v1/projects/route.ts
│   ├── error.tsx               # Global error boundary — REQUIRED
│   ├── not-found.tsx
│   └── layout.tsx              # Root layout (Server Component)
├── components/
│   ├── ui/                     # Design system primitives (Button, Input, Badge)
│   ├── common/                 # Shared across features (AppShell, Sidebar)
│   └── features/               # Feature-specific components
├── hooks/                      # Custom React hooks (useProjects, useDebounce)
├── services/                   # API call functions (projects.service.ts)
├── stores/                     # Zustand global state (projects.store.ts)
├── lib/                        # Utilities, helpers, error classes
├── types/                      # TypeScript type definitions
└── .env.example
```

#### page.tsx rule
*   `page.tsx` is always a Server Component (no `"use client"`) unless it has no async data.
*   `page.tsx` is a thin shell only — all state and interaction logic goes in a `*Content.tsx` client component.
*   *Example:* `app/dashboard/page.tsx` renders `<DashboardContent />` — the content file has `"use client"`.

---

### 4.2 Node.js / Express / Bun Backend [C-03 · P1 · Backend Developers]
```text
project-root/
├── src/
│   ├── routes/                 # Route definitions only — no logic
│   ├── controllers/            # Request/response handling
│   ├── services/               # Business logic — no HTTP here
│   ├── repositories/           # Database access — no business logic
│   ├── middleware/             # auth.ts, error-handler.ts, tenant.ts
│   ├── lib/                    # prisma.ts, logger.ts, errors.ts
│   ├── config/                 # env.ts — environment variable validation
│   └── app.ts                  # Express app setup (no listen() here)
├── tests/
│   ├── unit/
│   └── integration/
└── prisma/
    ├── schema.prisma
    └── migrations/
```

---

### 4.3 Python / FastAPI [C-04 · P1 · Python Developers]
```text
project-root/
├── app/
│   ├── main.py                 # FastAPI app, lifespan, middleware
│   ├── api/v1/                 # Route handlers per domain
│   ├── services/               # Business logic
│   ├── repositories/           # SQLAlchemy queries
│   ├── models/                 # SQLAlchemy ORM models
│   ├── schemas/                # Pydantic request/response schemas
│   └── core/                   # config.py, security.py, dependencies
├── alembic/versions/
├── tests/
└── .python-version             # pyenv version pin
```

---

### 4.4 React Native / Expo [C-05 · P1 · Mobile Developers]
```text
project-root/
├── app/                        # Expo Router file-based routing
│   ├── (auth)/login.tsx
│   ├── (tabs)/index.tsx
│   ├── _layout.tsx             # Root layout
│   └── +not-found.tsx
├── components/
│   ├── ui/
│   └── features/
├── hooks/
├── services/
├── stores/
├── constants/
├── assets/
├── app.json
└── eas.json                    # EAS Build config
```

---

## 🗄️ CHAPTER 5: Database Standards
*Schema Design, ORMs, Transactions, and Performance*

Database mistakes are uniquely dangerous because they can corrupt or permanently lose data. These standards make Fonix databases consistent, safe, and maintainable across every project.

### 5.1 Database Design [G-02 · P1 · Backend Developers]

#### Table naming
*   **DO:**
    *   `projects` — plural snake_case
    *   `user_push_tokens` — compound: domain first
    *   `billing_invoices` — clear and descriptive
*   **DON'T:**
    *   `Project` — not PascalCase
    *   `project` — not singular
    *   `tbl_users` — never use tbl_ prefix

#### Standard columns — every Fonix table includes these
```sql
-- Required on every table:
id         UUID         PRIMARY KEY DEFAULT gen_random_uuid()
created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
deleted_at TIMESTAMPTZ  -- soft delete (NULL = active)

-- On every multi-tenant table (required):
tenant_id  UUID         NOT NULL REFERENCES tenants(id)

-- Always index tenant_id:
CREATE INDEX idx_projects_tenant_id ON projects(tenant_id);
```

#### Indexing rules
*   Every foreign key column must have an index.
*   Every column used in `WHERE` clauses on large tables must have an index.
*   Add indexes with `CREATE INDEX CONCURRENTLY` on production tables — this avoids table locks.

---

### 5.2 Transactions [G-05 · P1 · Backend Developers]
Any operation that writes to more than one table **must** use a transaction. Without one, a failure midway leaves the database in a corrupted partial state.

```typescript
// Prisma transaction — all succeed or all fail:
const result = await prisma.$transaction(async (tx) => {
  const project = await tx.project.create({ data: projectData })
  await tx.activity.create({ data: { projectId: project.id, action: "created" } })
  await tx.notification.create({ data: { tenantId, projectId: project.id } })
  return project // if any step throws, ALL changes are rolled back
})
```

---

### 5.3 Preventing N+1 Queries [G-06 · P1 · Backend Developers]
N+1 queries are the most common database performance bug. Fetching a list of N items and then querying once per item = N+1 queries instead of 1.

```typescript
// ❌ N+1 — 1 query for projects + N queries for tasks:
const projects = await prisma.project.findMany({ where: { tenantId } })
for (const p of projects) {
  p.tasks = await prisma.task.findMany({ where: { projectId: p.id } })
}

// ✅ Single query with include:
const projects = await prisma.project.findMany({
  where: { tenantId },
  include: { tasks: true, _count: { select: { tasks: true } } }
})
```

---

## 🌐 CHAPTER 6: API Standards & Integrations
*REST Design, Auth, Documentation, Third-Party APIs, and Webhooks*

This chapter covers both the APIs Fonix builds and the third-party APIs Fonix integrates. *Note: H-04 (Third-Party Integration) now has two separate SOPs — one for backend developers and one for frontend developers. Both are included here.*

### 6.1 REST API Design Standards [H-01 · P1 · Backend Developers]
*   URLs are nouns, methods are verbs. `/api/v1/projects` not `/api/getProjects`
*   Always version APIs: `/api/v1/....` Increment to v2 only on breaking changes.
*   Plural resource names: `/api/v1/projects` not `/api/v1/project`
*   Nested routes for ownership: `/api/v1/projects/123/tasks`
*   Never verbs in paths: `PATCH` `{status:"archived"}` not `/api/v1/projects/123/archive`

#### Pagination — never return unlimited lists
Every list endpoint must have a maximum page size. No endpoint ever returns all records without a limit. Default page size: 20. Maximum: 100. Return 400 if client requests more than 100.

```json
// Standard paginated response:
{
  "success": true,
  "data": [...],
  "pagination": {
    "page": 2, 
    "limit": 20, 
    "total": 143,
    "totalPages": 8, 
    "hasNextPage": true
  }
}
```

```typescript
// Run count and data queries in parallel — never sequentially:
const [total, data] = await prisma.$transaction([
  prisma.project.count({ where }),
  prisma.project.findMany({ where, skip, take, orderBy })
])
```

---

### 6.2 Third-Party Integration Standards — Backend [H-04 Backend · P2]
Never call a third-party API directly from a route handler, controller, or service function. Every external service gets its own wrapper module.

#### The service wrapper pattern
```typescript
// src/services/email.service.ts — wraps Resend:
import { Resend } from "resend"
const resend = new Resend(env.RESEND_API_KEY)

export async function sendWelcomeEmail(to: string, name: string): Promise<void> {
  try {
    await resend.emails.send({
      from: "noreply@fonix.in",
      to,
      subject: `Welcome to Fonix, ${name}`,
      html: welcomeTemplate({ name }),
    })
    logger.info({ to, template: "welcome" }, "Email sent")
  } catch (error) {
    logger.error({ error, to }, "Failed to send welcome email")
    throw new AppError("Failed to send email", 500, "EMAIL_SEND_FAILED")
  }
}

// Route handler calls the wrapper — never the SDK directly:
await sendWelcomeEmail(user.email, user.name)
```

#### Retry logic for transient failures
*   Transient failures (network timeouts, 429 rate limits, 503 unavailable) should be retried with exponential backoff.
*   Use a maximum of 3 retries. Base delay: 1 second, doubling each attempt: 1s, 2s, 4s.
*   Never retry on 4xx errors — these indicate a problem with your request, not the service.

---

### 6.3 Third-Party Integration Standards — Frontend [H-04 Frontend · P2]
The same wrapper principle applies on the frontend. No component calls a third-party SDK directly.

#### Key differences from backend
*   Frontend integrations are often SDK-based (Stripe Elements, Razorpay Checkout, Sentry) rather than direct HTTP calls.
*   Never initialise third-party SDKs in component render paths — initialise once at the module level.
*   Keep API keys out of frontend code entirely. Use `NEXT_PUBLIC_` prefix only for keys that are intentionally public (Sentry DSN, Stripe publishable key). Never for secret keys.
*   Add timeout configuration to all HTTP clients. Default: 30 seconds for most APIs.

#### Rate limit handling
```typescript
// When a 429 is received, respect the Retry-After header:
if (response.status === 429) {
  const retryAfter = parseInt(response.headers.get("Retry-After") ?? "60")
  await sleep(retryAfter * 1000)
  return await fetchWithRetry(url, options, retriesLeft - 1)
}
```

---

### 6.4 Webhook Handling Standards [H-05 · P2 · Backend Developers]
Webhooks are how third-party services tell you something happened. They must be handled securely and idempotently.

#### The four rules of webhook handling
1.  **Verify the signature first** — before processing anything. Every provider (Stripe, Razorpay) sends a signature header.
2.  **Respond 200 immediately** — before processing. Slow responses cause retries which cause duplicate processing.
3.  **Process idempotently** — check if the event has already been processed. Store event IDs and ignore duplicates.
4.  **Process asynchronously** — enqueue the work, do not process in the webhook handler itself.

```typescript
// Stripe webhook example:
router.post("/webhooks/stripe", express.raw({ type: "application/json" }),
  async (req, res) => {
    const sig = req.headers["stripe-signature"]
    let event
    try {
      event = stripe.webhooks.constructEvent(req.body, sig, env.STRIPE_WEBHOOK_SECRET)
    } catch {
      return res.status(400).send("Invalid signature")
    }
    res.json({ received: true }) // respond immediately
    await webhookQueue.add(event.type, event) // process async
  }
)
```

---

## 🛡️ CHAPTER 7: Security
*OWASP, Input Validation, Payments, File Uploads, RBAC, GDPR*

Security is not a checklist you complete at the end. It is a mindset applied to every function you write. Every developer at Fonix is responsible for the security of the code they write.

### 7.1 The Non-Negotiable Security Rules [I-01 · P1 · Everyone]
*Violating any of these is a security incident — report to CTO immediately*
1.  Never store secrets in code. Git history is permanent — a deleted commit must still be treated as exposed.
2.  Never trust client input. Validate and sanitise every input on the server.
3.  Never build SQL by string concatenation. Use the ORM or parameterised queries.
4.  Never store passwords in plain text. Use bcrypt (cost factor 10+) or Argon2.
5.  Never log sensitive data: passwords, tokens, card numbers, PII.
6.  Never expose stack traces to users in production.
7.  Card data never touches your server. Use Razorpay Checkout or Stripe Elements.
8.  HTTPS everywhere. No HTTP in production or staging.

---

### 7.2 Input Validation [I-06 · P1 · Backend Developers]
Client-side validation is a courtesy. Server-side validation is the security measure. Always validate on the server.

```typescript
// Zod — validate every incoming request body:
const createProjectSchema = z.object({
  name: z.string().min(1).max(100),
  description: z.string().max(500).optional(),
  status: z.enum(["active","pending","completed"]),
})

router.post("/projects", authenticateJWT, async (req, res) => {
  const result = createProjectSchema.safeParse(req.body)
  if (!result.success) {
    return res.status(400).json({
      success: false,
      error: { code: "VALIDATION_ERROR", details: result.error.format() }
    })
  }
  // result.data is now safe and fully typed
})
```

---

### 7.3 Payment Security [I-04 · P1 · Everyone]
#### The golden rule — never handle card data
Card numbers, CVV codes, and expiry dates must NEVER pass through your server. Use Razorpay Checkout or Stripe Elements — users enter payment details directly into the provider's hosted UI.
Your server only handles order IDs, payment confirmation webhooks, and signed tokens. Using hosted payment UI keeps Fonix in PCI DSS SAQ A. Handling card data yourself requires SAQ D — a full annual audit.

---

### 7.4 File Upload Security [I-05 · P1 · Backend Developers]
*   Validate file type by reading magic bytes using the `file-type` npm package. Never trust the `Content-Type` header.
*   Rename all uploaded files to UUID + validated extension. Never serve user-supplied filenames.
*   Store in S3 only — never on the application server disk.
*   Private files: serve via signed URLs with 5–15 minute expiry.
*   Maintain an explicit whitelist of allowed file types. Reject everything not on it.

---

### 7.5 RBAC and GDPR [I-02 · P2 | I-03 · P2 · Everyone]

#### Role-Based Access Control
*   Check authorisation on every API request — do not rely on client-side role checks.
*   Always extract the user's role and `tenantId` from the verified JWT. Never trust these values from the request body.
*   Row-level security: every multi-tenant query must filter by `tenantId` from the token.

#### GDPR basics for developers
*   Any data that can identify an EU/UK user is personal data: name, email, IP address, device ID.
*   **Right to erasure:** your code must be able to delete or anonymise all personal data for a given user.
*   **Data minimisation:** only store what you actually need. Never store PII in logs or analytics events.

---

## 🧪 CHAPTER 8: Testing & Quality Assurance
*Self-Testing, Unit Tests, QA, Bug Reporting, Cross-Browser, Mobile*

QA exists to catch what developers miss — not to do the developer's own testing. Every developer tests their own work before it goes to QA. The goal: reach QA with no obvious bugs.

### 8.1 Developer Self-Testing Checklist [J-01 · P1 · Everyone]
*Run every item on this checklist before creating a PR. No exceptions.*

| Item | What to check |
| :--- | :--- |
| **Happy path** | Primary use case works end-to-end for the correct user role. |
| **Empty state** | What shows when there is no data? Empty array not null. Message not blank screen. |
| **Error state** | What shows when an API call fails? Does the UI communicate the error? |
| **Edge cases** | Empty string, maximum length, special characters, 0, null, negative numbers. |
| **Loading state** | Loading indicator visible during async operations. Disappears when done. |
| **Responsive** | Layout works at 375px (mobile), 768px (tablet), 1280px (desktop). |
| **Console** | No errors or warnings in browser console during normal use. |
| **Network tab** | API calls use correct HTTP method, return expected status codes. |
| **Permissions** | Tested as the correct user role — not as admin when testing a regular user feature. |

---

### 8.2 Bug Severity and Reporting [J-04 · P1 · Everyone]
| Level | Definition | Example | Response time |
| :--- | :--- | :--- | :--- |
| **P0 — Critical** | Production down or data at risk. | Login broken for all users. | Immediate — drop everything |
| **P1 — High** | Core feature broken, no workaround. | Cannot create projects. | Same day — notify Team Lead now |
| **P2 — Medium** | Feature degraded, workaround exists. | Export is slow. | Current sprint |
| **P3 — Low** | Cosmetic, no functional impact. | Button misaligned by 2px. | Next sprint |

#### Required bug report format
```text
TITLE: [P1] Project list crashes when filtering by "completed" status

STEPS TO REPRODUCE:
1. Log in as any user
2. Navigate to /projects
3. Click Status filter -> select "Completed"
4. Page crashes with white screen

EXPECTED: Project list filters to completed projects
ACTUAL: White screen — console: TypeError: Cannot read properties of undefined

ENVIRONMENT: Staging | Browser: Chrome 122 | Date: 05 Apr 2026
Screenshot: [attached] | Console error: [pasted]
```

---

## ✉️ CHAPTER 9: Notifications — Email, Push & SMS
*New: M-04 is now split into Backend and Frontend SOPs*

This chapter covers both the Backend SOP (M-04 Backend) — service layer, templates, and delivery infrastructure — and the Frontend SOP (M-04 Frontend) — channel selection, permission flows, and compliance. Read both if you are a full-stack developer.

### 9.1 Which Channel for Which Use Case [M-04 Both · P2]
| Channel | Use for | Do NOT use for |
| :--- | :--- | :--- |
| **Email (Resend)** | Account lifecycle (welcome, verify, password reset), receipts, invoices, weekly digests, any notification needing a permanent record. | High-frequency updates that would overwhelm the inbox, push-worthy alerts. |
| **Push (Expo)** | New assignment, task due reminder, project status change, export ready — things that are time-sensitive and short. | Marketing messages, routine low-priority updates, anything that can wait until next login. |
| **SMS (Twilio)** | OTP/2FA, critical security alerts, payment failure on a card. Use sparingly. | Routine notifications — SMS is expensive per message and feels intrusive for non-critical alerts. |

#### The dev/staging suppression rule — critical
Development and staging environments must NEVER send real emails, push notifications, or SMS to real users.
*   **In development:** suppress all sends. Log the notification content to the console instead.
*   **In staging:** redirect all messages to a test sink (`STAGING_EMAIL_OVERRIDE`, staging device only).
*   *This must be built into the notification service function — not left to individual developers to remember.*

---

### 9.2 Email with Resend [M-04 Backend · P2]
Fonix uses Resend as the transactional email provider. All emails go through the email service wrapper — never directly through the Resend SDK.

```typescript
// services/email.service.ts
export async function sendPasswordReset(to: string, resetUrl: string): Promise<void> {
  // Guard: never send to real users on non-production
  const recipient = env.NODE_ENV === "production" ? to : env.STAGING_EMAIL_OVERRIDE
  await resend.emails.send({
    from: "noreply@fonix.in",
    to: recipient,
    subject: "Reset your Fonix password",
    html: passwordResetTemplate({ resetUrl, expiresIn: "1 hour" }),
  })
}
```

#### Email template standards
*   Every transactional email must include: Fonix logo, clear subject, primary action button, plain-text fallback.
*   Unsubscribe link is required on all non-transactional emails (digests, marketing).
*   Test rendering in Gmail, Outlook, and Apple Mail before deploying email templates.

---

### 9.3 Push Notifications with Expo [M-04 Frontend · P2]
Push notifications require explicit user permission. The permission flow is as important as the notification itself.

#### Permission request rules
*   Never request push permission on app first launch. Ask after the user has experienced value — after a meaningful action.
*   Explain why you are asking before the system prompt appears. Users who understand the value accept more.
*   If the user denies permission, do not ask again immediately. Respect their choice.

#### Push notification payload standards
```json
// Every push notification includes:
{
  "to": "[expo-push-token]",
  "title": "Project assigned to you", // short, clear
  "body": "E-Commerce App — Sprint 4 has started", // one line
  "data": { "screen": "projects", "projectId": "abc-123" }, // deep link target
  "sound": "default",
  "badge": 1
}
```

#### SMS with Twilio — use sparingly
*   SMS is reserved for: OTP/2FA, critical security alerts, and payment failure notifications.
*   Every SMS must include your company name: *"Fonix: Your verification code is 847291"*
*   Include opt-out instructions for any non-transactional SMS: *"Reply STOP to unsubscribe"*
*   DLT registration is required in India for commercial SMS. Ensure templates are registered before sending.

---

## 🚢 CHAPTER 10: Deployment & CI/CD
*Environments, Pipeline, Pre-Deploy Checklist, and Rollback*

Deployment mistakes are expensive and visible to clients. These standards make deployments predictable, and ensure that when something goes wrong, the response is fast and methodical.

### 10.1 Environment Strategy [K-01 · P1 · Everyone]
| Strategy | Development | Staging | Production |
| :--- | :--- | :--- | :--- |
| **Purpose** | Write and test code | Verify before release | Real users, real money |
| **Branch** | Feature branch | `develop` — auto-deploys on merge | `main` — manual approval gate |
| **Migrations** | Runs locally on merge | Runs on staging DB on merge | Runs on prod DB on deploy |

---

### 10.2 Pre-Deploy Checklist [K-02 · P1 · Team Lead]
*No production deployment without every item checked*
*   QA has signed off — sign-off comment exists in the ticket.
*   Code has been running on staging for at least 1 hour without Sentry errors.
*   If migrations included: they have run successfully on staging first.
*   If new environment variables required: already set in production environment.
*   No live API keys in staging configuration (and no staging keys in production).
*   Deployment window: Tuesday to Thursday, 10am–3pm IST.
*   Team Lead or CTO available for 15 minutes post-deploy to monitor.
*   You know the rollback procedure before you press deploy.

---

### 10.3 Rollback Procedure [K-04 · P1 · Team Lead]
#### When in doubt: rollback first. Investigate second.
Rolling back is not failure. Leaving users with a broken production while you investigate is failure. If something goes wrong in production: assess severity, rollback, then investigate. Never attempt to fix a P0/P1 bug live on production. Rollback, then fix in a branch.

#### Vercel rollback (fastest — under 2 minutes):
1.  Dashboard: `vercel.com/[org]/[project] -> Deployments`
2.  Find last working deployment -> `...` menu -> *"Promote to Production"*
3.  Or via CLI:
    ```bash
    vercel ls --prod        # list recent deployments
    vercel promote [url]    # promote a specific deployment
    ```

#### After rollback — do within 15 minutes
1.  Confirm application is healthy — test login, primary feature, 2-3 user flows.
2.  Confirm Sentry error rate returned to pre-deploy baseline.
3.  Post in team channel: *"[Project] rolled back at [time]. Reason: [brief]. Fix in progress."*
4.  If P0/P1: notify CTO directly — do not rely on the channel message alone.

---

## 🚨 CHAPTER 11: Production Incidents
*Response, Hotfixes, Post-Mortems, and Monitoring*

When something breaks in production, the quality of your response matters as much as the fix. A calm, methodical response limits damage. A panicked improvised one makes it worse.

### 11.1 Incident Response [L-01 · P1 · Everyone]
| Severity | Definition | First action | Escalation |
| :--- | :--- | :--- | :--- |
| **P0 — Critical** | Production down or data at risk. | Notify Team Lead and CTO now. | All hands |
| **P1 — High** | Core feature broken, no workaround. | Notify Team Lead in 15 min. | Team Lead leads |
| **P2 — Medium** | Feature degraded, workaround available. | Log ticket, fix this sprint. | Next standup |
| **P3 — Low** | Minor issue, no functional impact. | Log ticket, next sprint. | No escalation |

#### The four phases
1.  **Detect and assess:** Confirm real, determine severity, who is affected?
2.  **Communicate:** Notify right people based on severity. Post in channel.
3.  **Contain:** Rollback if P0/P1. Fix-forward if faster and safer.
4.  **Post-mortem:** Blameless post-mortem within 48 hours for P0 and novel P1s.

---

### 11.2 Hotfix Process [L-02 · P2 · Team Lead]
A hotfix is an emergency fix deployed directly to production without going through the normal sprint cycle. Use it only for P0 and P1 issues.

*   Branch from `main`, not `develop`: `git checkout -b hotfix/FON-412-null-crash main`
*   Abbreviated review: Team Lead reviews within 15 minutes for P0, 1 hour for P1.
*   Merge to `main` first (to fix production), then immediately merge to `develop` (to keep them in sync).
*   Create a follow-up ticket for a thorough fix if the hotfix is a temporary patch.

---

## 🛠️ CHAPTER 12: Advanced Features
*Multi-Tenancy, Background Jobs, Payments, File Uploads, Real-Time, Pagination*

Read the SOP for each feature type before building it for the first time. These SOPs exist because every feature in this section has a non-obvious correct way to build it — and several obvious wrong ways.

### 12.1 Multi-Tenancy [M-01 · P2 · Backend Developers]
#### The isolation rule
Every query against a multi-tenant table must include `WHERE tenant_id = [id from JWT]`. The `tenantId` must come from the verified JWT — never from the request body. A client can forge a request body. If even one query is missing the `tenantId` filter, tenant A can see tenant B's data.

*   **CORRECT:**
    ```typescript
    // tenantId from JWT middleware:
    const projects = await prisma.project.findMany({
      where: { tenantId: req.tenant.id } // from authenticateJWT middleware
    })
    ```
*   **WRONG:**
    ```typescript
    // tenantId from request body:
    const projects = await prisma.project.findMany({
      where: { tenantId: req.body.tenantId } // attacker can send any tenantId
    })
    ```

---

### 12.2 Payment Integration [M-05 · P2 + I-04 · P1]
*Read both M-05 (implementation) AND I-04 (security) before touching payments*
*   Card data never touches your server. Use Razorpay Checkout or Stripe Elements.
*   The webhook is the authoritative payment confirmation — not the client-side callback.
*   Always verify the webhook signature before processing.
*   Use idempotency keys on payment creation to prevent duplicate charges.

#### Order state machine — every payment flows through this
```text
PENDING → PROCESSING → COMPLETED
  ↓
FAILED

COMPLETED → REFUND_REQUESTED → REFUNDED
```

#### Rules:
1.  FAILED payments can never become COMPLETED.
2.  Duplicate webhook events are silently ignored (idempotency).
3.  Webhook is authoritative — not the client-side callback.

---

### 12.3 Background Jobs [M-02 · P2 · Backend Developers]
Long-running operations — PDF generation, bulk email, data exports, AI processing — must run as background jobs, not in API route handlers. An API route that takes more than 5 seconds will time out.

```typescript
// Route handler — returns immediately with 202:
router.post("/exports", authenticateJWT, async (req, res) => {
  const job = await exportQueue.add("generate-pdf", {
    tenantId: req.tenant.id, 
    reportId: req.body.reportId
  })
  res.status(202).json({ success: true, data: { jobId: job.id } })
})

// Worker — processes in background:
const worker = new Worker("exports", async (job) => {
  const pdf = await generateReport(job.data.reportId)
  const key = await uploadToS3(pdf)
  await notifyUser(job.data.tenantId, key)
}, { connection: redis })
```

---

### 12.4 Pagination, Filtering, Sorting [M-07 · P2 · Backend Developers]

#### Real-Time Features [M-03 · P3]
| Approach | Use when | Example |
| :--- | :--- | :--- |
| **Polling** | 30-second updates are acceptable. Simple, scales perfectly. | Dashboard stats refresh |
| **Server-Sent Events** | Server needs to push events to client one-way. Auto-reconnect. | AI streaming, export progress |
| **WebSockets (Socket.io)** | Bidirectional real-time needed. | Live collaboration, chat |

---

## 📖 CHAPTER 13: Documentation & Handover
*README Standards and Technical Handover Documentation*

### 13.1 Project README Standards [N-01 · P2 · Everyone]
Every Fonix project must have a README that enables any developer to clone, run, and contribute without asking anyone for help.

#### Required sections
*   **Project description** — one paragraph: what it does, who uses it, and why it exists.
*   **Prerequisites** — exact Node version (`.nvmrc`), Python version (`.python-version`), required global tools.
*   **Setup** — exact commands from clone to running locally: clone, install, copy `.env.example` to `.env`, seed, run dev.
*   **Environment Variables** — every variable in table format: key, description, example value, required or optional.
*   **Project Structure** — key folders and what they contain.
*   **Development Workflow** — branching strategy, how to create PRs, how CI/CD works.
*   **Deployment** — how to deploy to staging, how to deploy to production, who has access.
*   **Troubleshooting** — common setup errors and how to fix them.

---

### 13.2 Technical Handover Documentation [N-02 · P2 · Everyone]
When you leave a project, you create a technical handover document so the next developer can own it without losing knowledge.

#### Required at least 5 business days before your last day on any project
This is not optional. Leaving without a handover document is a professional failure. The handover document must be reviewed and signed off by the Team Lead. If you are the only person who knows something, document it. That is the point of this document.

#### The handover document must include
*   **Architecture overview:** system components, how they connect, technology choices and rationale.
*   **Known technical debt:** what corners were cut, where the bodies are buried, what to watch out for.
*   **Critical dependencies:** third-party services, their APIs, credentials location, what happens if they go down.
*   **Deployment process:** exact steps, who has access, what to do if the deployment fails.
*   **Codebase gotchas:** non-obvious things, workarounds, things that broke before and how they were fixed.
*   **Open items:** incomplete features, deferred bugs, decisions that were not made.

---

## 📋 CHAPTER 14: Quick Reference
*P1 Rules · Complete SOP Index · New Developer Reading Plan*

Print this chapter. Pin it up. The P1 rules are what every developer must know without looking anything up.

### 14.1 The P1 Rules — Know These Without Asking
1.  No code merges to develop or main without a PR with passing CI and an approved review.
2.  Secrets, API keys, and passwords are never committed to git. If it happens, rotate immediately.
3.  Every user-facing input is validated on the server — regardless of client-side validation.
4.  Every API route verifies the JWT and checks authorisation before any business logic.
5.  Card data never passes through your server. Use Razorpay Checkout or Stripe Elements.
6.  No `console.log` in production code. Use the structured logger (Pino / loguru).
7.  No production deployment outside safe hours (Tue–Thu 10am–3pm IST) without CTO approval.
8.  No live API keys on staging. No staging keys on production.
9.  Any write to more than one table uses a database transaction.
10. Every production deployment has a 15-minute monitoring window immediately after.
11. When in doubt about production: rollback first, investigate second.
12. All significant decisions — architecture, scope, estimate — are written in the ticket. Never only verbal.
13. No development task starts without a written ticket in the issue tracker.
14. Estimates are honest — not what the deadline requires.
15. If blocked for more than one day: raise it in standup. Do not sit on it.

---

### 14.2 Complete SOP Index — All 87 SOPs
| ID | Title | Priority | Who Reads It |
| :--- | :--- | :--- | :--- |
| **A-01** | How the Web Works — HTTP, DNS, Request/Response | P1 | Everyone |
| **A-02** | What is a REST API and How to Think About It | P1 | Everyone |
| **A-03** | How Authentication Works End to End | P1 | Everyone |
| **A-04** | Design to Dev Handoff | P1 | FE + Designers |
| **A-05** | How to Read an Error — Stack Traces, Console Errors | P1 | Everyone |
| **A-06** | Naming Things — Variables, Functions, Files, Databases | P1 | Everyone |
| **A-07** | Environment Variables and Secrets Management | P1 | Everyone |
| **A-08** | Git Basics, Branching Strategy, and .gitignore | P1 | Everyone |
| **A-09** | Common Beginner Mistakes and Dos/Don'ts | P1 | Everyone |
| **A-10** | Development, Staging, and Production Environments | P1 | Everyone |
| **A-11** | What Technical Debt Is and Why Shortcuts Compound | P1 | Everyone |
| **A-12** | How to Ask for Help and When | P1 | Everyone |
| **B-01** | Task Creation and Acceptance Criteria | P1 | Everyone + BA |
| **B-02** | Sprint Planning and Task Estimation | P1 | Everyone + BA |
| **B-03** | Daily Standup and Developer Communication | P2 | Everyone |
| **B-04** | Figma MCP Usage for Developers | P2 | Frontend devs |
| **B-05** | Scope Change and Change Order Protocol | P2 | TL + BA |
| **B-06** | New Developer Onboarding Checklist | P1 | New joiners |
| **B-07** | Pull Request Process | P1 | Everyone |
| **C-01** | React and Next.js Project Structure | P1 | FE + FS devs |
| **C-02** | Vue.js Project Structure | P1 | FE + FS devs |
| **C-03** | Node.js / Express / Bun Project Structure | P1 | BE + FS devs |
| **C-04** | Python / Django / FastAPI Project Structure | P1 | BE + FS devs |
| **C-05** | React Native / Expo Project Structure | P1 | Mobile devs |
| **C-06** | AI/ML Integration Project Structure | P2 | BE + FS devs |
| **D-01** | Component and Module Naming Conventions | P1 | FE devs |
| **D-02** | CSS Standards — Internal-Only Rule, Tailwind, No CDN | P1 | FE devs |
| **D-03** | Frontend Component Standards — Reusability and Props | P1 | FE devs |
| **D-04** | Frontend Error Handling — Toast, Loading, Error Boundaries | P1 | FE devs |
| **D-05** | State Management — Zustand, useState, URL State | P1 | FE devs |
| **D-06** | Pixel-Perfect Implementation and Figma Matching | P2 | FE devs |
| **D-07** | Responsive Design Standards | P2 | FE devs |
| **F-01** | JavaScript and TypeScript Standards | P1 | JS/TS devs |
| **F-02** | Python Coding Standards | P1 | Python devs |
| **F-03** | Backend Error Handling — AppError, Middleware | P1 | BE devs |
| **F-04** | How Async/Await Works and Why It Matters | P1 | Everyone |
| **F-05** | Code Documentation Standards | P2 | Everyone |
| **F-06** | Logging Standards — Pino, loguru, Structured JSON | P1 | BE devs |
| **G-01** | Database Fundamentals | P1 | BE devs |
| **G-02** | Database Design Standards — Naming, Indexes, Audit Fields | P1 | BE devs |
| **G-03** | Prisma ORM — Setup, Schema, Migrations | P1 | Node/TS BE |
| **G-04** | SQLAlchemy and Django ORM | P1 | Python BE |
| **G-05** | Database Transactions | P1 | BE devs |
| **G-06** | Preventing N+1 Queries | P1 | BE devs |
| **G-07** | Caching Strategy and Standards | P2 | BE devs |
| **H-01** | REST API Design Standards | P1 | BE devs |
| **H-01*** | REST API Design (second version — check with CTO) | P1 | BE devs |
| **H-02** | API Authentication and Security | P1 | BE devs |
| **H-03** | API Documentation Standards | P2 | BE devs |
| **H-04 BE** | Third-Party API Integration Standards (Backend) | P2 | BE devs |
| **H-04 FE** | Third-Party API Integration Standards (Frontend) | P2 | FE + FS devs |
| **H-05** | Webhook Handling Standards | P2 | BE devs |
| **I-01** | OWASP Top 10 for Developers | P1 | Everyone |
| **I-02** | Role-Based Access Control (RBAC) | P2 | BE devs |
| **I-03** | GDPR for Developers | P2 | Everyone |
| **I-04** | Payment Integration Security | P1 | Everyone |
| **I-05** | File Upload Security | P1 | BE devs |
| **I-06** | Input Validation and Sanitisation | P1 | BE devs |
| **J-01** | Developer Self-Testing Checklist | P1 | Everyone |
| **J-02** | Unit and Integration Testing Standards | P2 | Everyone |
| **J-03** | QA Testing Process — From Dev to Client | P1 | QA + TL |
| **J-04** | Bug Reporting Standards — Severity and Format | P1 | Everyone |
| **J-05** | Cross-Browser and Cross-Device Testing | P2 | FE + QA |
| **J-06** | React Native Testing Process | P2 | Mobile + QA |
| **K-01** | Environment Strategy — Dev, Staging, Production | P1 | Everyone |
| **K-02** | Deployment Process and Pre-Deploy Checklist | P1 | Team Lead |
| **K-03** | CI/CD Pipeline Standards | P2 | Team Lead |
| **K-04** | Rollback Procedure | P1 | Team Lead |
| **L-01** | Production Incident Response | P1 | Everyone |
| **L-02** | Hotfix Process | P2 | Team Lead |
| **L-03** | Post-Mortem Process | P2 | Team Lead |
| **L-04** | Monitoring and Alerting Setup Standards | P2 | Team Lead |
| **M-01** | Multi-Tenancy Architecture and Tenant Isolation | P2 | BE + FS devs |
| **M-02** | Background Jobs and Queue Processing | P2 | BE + FS devs |
| **M-03** | WebSockets and Real-Time Features | P3 | BE + FE devs |
| **M-04 BE** | Email, Push Notifications, and SMS (Backend) | P2 | BE + FS devs |
| **M-04 FE** | Email, Push Notifications, and SMS (Frontend) | P2 | FE + FS devs |
| **M-05** | Payment Integration — Razorpay and Stripe | P2 | FE + BE devs |
| **M-06** | File Upload and Storage | P2 | FE + BE devs |
| **M-07** | Pagination, Filtering, and Sorting | P2 | BE devs |
| **M-08** | Internationalisation (i18n) and Localisation (l10n) | P3 | FE + Mobile |
| **M-09** | API Versioning and Backwards Compatibility | P3 | BE + TL |
| **N-01** | Project README Standards | P2 | Everyone |
| **N-02** | Technical Handover Documentation | P2 | Everyone + TL |
| **REF-GIT-01** | Git Branching Strategy Quick Reference Card | REF | Everyone |
| **REF-CR-01** | Code Review Checklist (Author + Reviewer) | REF | Everyone |

---

### 14.3 New Developer Reading Plan
*   **Day 1:** This handbook (start to finish). B-06 (Onboarding checklist with Team Lead). A-07 (Environment Variables — set up your `.env`). REF-GIT-01 (Branching reference — pin to your workspace).
*   **Days 2–3:** A-01 How the Web Works. A-02 REST APIs. A-03 Authentication. A-08 Git Basics. Read in order — each builds on the last.
*   **Days 4–5:** A-06 Naming. F-04 Async/Await. A-09 Common Mistakes. A-10 Environments. A-11 Technical Debt. A-12 Asking for Help.
*   **Week 2:** B-01 Task Creation. B-02 Sprint Planning. B-03 Standup. B-07 Pull Request. REF-CR-01 Code Review Checklist. Your stack structure SOP: C-01 (React), C-02 (Vue), C-03 (Node), C-04 (Python), C-05 (React Native).
*   **Week 3-4:** F-01 TypeScript (or F-02 Python). I-01 OWASP Top 10. I-06 Input Validation. G-02 Database Design (BE). D-02 CSS Standards (FE). D-01, D-03, D-04, D-05 (FE).
*   **Month 2+:** Feature-driven reading: payments → M-05 + I-04. File uploads → M-06 + I-05. First production deploy → K-02 + K-04. Notifications → M-04 BE + M-04 FE. Incident response → L-01. Real-time → M-03. Database transactions → G-05.
