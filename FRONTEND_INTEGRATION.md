# Frontend Integration Document

## Multimodal Knowledge Platform

Version: 1.0  
Backend API Base: `/api/v1`  
Prepared for: Frontend implementation handoff

## 1) Project Overview

### What the platform does
The Multimodal Knowledge Platform is an AI knowledge assistant focused on grounded answers from user-uploaded content. Today, the production backend is optimized for PDF Retrieval-Augmented Generation (RAG): users upload PDFs, the system ingests and indexes them, and chat responses are generated with explicit source citations.

### Current capabilities
- User authentication with JWT and optional OAuth (Google, GitHub)
- PDF upload and ingestion pipeline
- Retrieval-augmented chat (`/chat/query`) with citations
- Conversation persistence (create/list/get/delete conversations)
- Session security with refresh rotation and replay detection
- Telemetry/observability hooks (OpenTelemetry + domain metrics)
- Retrieval evaluation framework and quality tooling

### Future roadmap
- Video RAG
- Image RAG
- Audio understanding
- PPT ingestion and retrieval
- Unified multimodal retrieval across document types

## 2) System Architecture

### Flow
User  
↓  
Next.js Frontend  
↓  
FastAPI Backend  
↓  
PostgreSQL  
↓  
ChromaDB  
↓  
LLM

### Layer responsibilities
- User
  - Authenticates, uploads documents, asks questions, reviews citations, manages conversations.
- Next.js Frontend
  - UI rendering, routing, form validation, optimistic UX, API integration, auth token lifecycle, state orchestration.
- FastAPI Backend
  - Auth/session management, document ingestion orchestration, retrieval + grounding logic, chat response generation, conversation persistence APIs.
- PostgreSQL
  - Source of truth for users, sessions, OAuth state, conversations/messages, document ownership/metadata, ingestion records.
- ChromaDB
  - Vector store for embeddings and semantic retrieval.
- LLM
  - Final response synthesis from retrieved context with citation grounding.

## 3) Frontend Tech Stack (Recommended)

- Next.js 15
  - App Router + server/client boundaries, streaming-ready architecture, strong DX for production apps.
- TypeScript
  - Strict contracts for API payloads and UI state, fewer runtime integration bugs.
- Tailwind CSS
  - Fast, consistent, token-driven styling and responsive implementation.
- shadcn/ui
  - Accessible primitives with composability, ideal for premium UI systems.
- React Query (TanStack Query)
  - Server-state caching, retries, background refresh, stale management.
- Zustand
  - Lightweight client-state store for auth/session UX, UI state, conversation-side interactions.
- React Hook Form
  - Performant forms with low rerender overhead.
- Zod
  - Shared validation schemas for inputs and API response parsing.

## 4) Authentication Flow

## Endpoints
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/google`
- `GET /api/v1/auth/github`
- `GET /api/v1/auth/me` (recommended for session bootstrap)

### Token model
- Access Token
  - Short-lived JWT for authenticated API calls.
  - Backend default expiry: `JWT_ACCESS_TOKEN_MINUTES=15`.
- Refresh Token
  - Longer-lived JWT-like token used only to mint new access+refresh pair.
  - Backend default expiry: `JWT_REFRESH_TOKEN_MINUTES=10080` (7 days).

### Session rotation and replay protection
- Every successful `/auth/refresh` rotates refresh token.
- Reusing an old refresh token is treated as replay.
- On replay detection, backend revokes the whole session family and returns `401` with code `refresh_replay_detected`.

### Logout flow
- Frontend sends current refresh token to `/auth/logout`.
- Backend revokes that session.
- Frontend clears all auth state (memory + storage) and routes to login.

### Request/response examples

1. Register  
Request:
```json
{
  "email": "user@example.com",
  "password": "password123",
  "name": "User"
}
```
Response (`UserMe`):
```json
{
  "id": "4f52d9f1-7c5e-4d56-8a84-94a15fe2c7f8",
  "email": "user@example.com",
  "name": "User",
  "provider": null,
  "provider_account_id": null
}
```

2. Login  
Request:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```
Response (`AuthTokens`):
```json
{
  "access_token": "<jwt>",
  "refresh_token": "<refresh>",
  "token_type": "bearer"
}
```

3. Refresh  
Request:
```json
{
  "refresh_token": "<refresh>"
}
```
Response:
```json
{
  "access_token": "<new_jwt>",
  "refresh_token": "<new_refresh>",
  "token_type": "bearer"
}
```

4. Logout  
Request:
```json
{
  "refresh_token": "<refresh>"
}
```
Response:
```json
{
  "ok": true
}
```

5. OAuth entry
- `GET /auth/google` and `GET /auth/github` return provider authorization data (URL/state/nonce flow managed by backend).
- Frontend should redirect user to returned authorization URL.

## 5) Application Pages

## Login Page
### Requirements
- Email/password login
- OAuth sign-in buttons (Google/GitHub, feature-flag aware)
- “Remember me” option (frontend only, controls persistence mode)

### Components
- Auth card
- Email/password fields
- Submit button + loading state
- OAuth buttons
- Inline error alert

### States
- Idle
- Submitting
- Success (route to dashboard)
- Error (invalid creds, rate limited, network)

### Validation
- Email format
- Password non-empty

## Signup Page
### Requirements
- Name, email, password
- Post-register flow to login page or auto-login (team choice)

### Components
- Signup form
- Password strength hint
- Terms acknowledgment

### States
- Idle / Submitting / Success / Error

### Validation
- Email format
- Password min length 8
- Name optional but if present trim whitespace

## Dashboard
### Must show
- Uploaded documents list
- Recent conversations
- User profile snippet (`/auth/me`)

### Suggested widgets
- “New Chat” CTA
- “Upload Document” CTA
- Usage/health status badges (optional)

## Upload Center
### Features
- Drag-and-drop PDF upload
- Manual file picker fallback
- Progress indicator
- Success state (document metadata summary)
- Error state (mime/size/extraction failures)

### Notes
- Backend endpoint: multipart form `POST /documents/upload`
- Optional `document_id` form field for idempotent replacement semantics

## Chat Workspace
### Features
- Conversation sidebar (list/create/delete)
- Main message area
- Input composer
- Source citation rendering per assistant response
- Typing indicator
- Loading/skeleton states

### Data behavior
- Send prompt to `/chat/query`
- Include `conversation_id` when chat is tied to a conversation
- Persist messages via backend side effect in query route

## Citation Viewer
### Features
- Filename
- Page number
- Evidence snippet
- Expand source context panel

### Citation object contract
- `filename`
- `page_number`
- `chunk_id`
- `snippet`

## Settings Page
### Sections
- Profile info
- Security/session actions (logout all coming later if exposed)
- OAuth connections visibility (connected provider metadata)
- Theme settings (dark/light/system)

## 6) API Integration Guide

All errors follow:
```json
{
  "error": {
    "code": "some_code",
    "message": "Human readable message",
    "details": {},
    "correlation_id": "uuid"
  }
}
```

### `GET /api/v1/health`
- Purpose: service readiness probe
- Usage notes: call at app startup for status indicator
- Error handling: treat failure as “backend unavailable”

### `POST /api/v1/auth/register`
- Purpose: create user account
- Request:
```json
{"email":"user@example.com","password":"password123","name":"User"}
```
- Response: `UserMe`
- Frontend notes: do not store tokens (register does not return tokens)
- Error notes: show field-level message for invalid email/password

### `POST /api/v1/auth/login`
- Purpose: issue access+refresh tokens
- Request:
```json
{"email":"user@example.com","password":"password123"}
```
- Response:
```json
{"access_token":"...","refresh_token":"...","token_type":"bearer"}
```
- Frontend notes: save tokens, then call `/auth/me`
- Error notes: handle `401`, `429 rate_limited`

### `POST /api/v1/auth/refresh`
- Purpose: rotate and renew session tokens
- Request:
```json
{"refresh_token":"..."}
```
- Response: new token pair
- Frontend notes: serialize refresh requests to avoid race conditions
- Error notes: if `refresh_replay_detected` or `invalid_refresh`, hard logout

### `POST /api/v1/auth/logout`
- Purpose: revoke current refresh token session
- Request:
```json
{"refresh_token":"..."}
```
- Response:
```json
{"ok":true}
```
- Frontend notes: clear state regardless of response

### `GET /api/v1/auth/me`
- Purpose: fetch current user profile
- Request: bearer access token
- Response:
```json
{
  "id":"uuid",
  "email":"user@example.com",
  "name":"User",
  "provider":"google",
  "provider_account_id":"123456"
}
```
- Frontend notes: use for session bootstrap and header profile

### `GET /api/v1/auth/google` and `GET /api/v1/auth/github`
- Purpose: start OAuth flow
- Response: provider auth payload from backend (includes redirect URL metadata)
- Frontend notes: redirect to returned provider URL, then handle callback route in frontend
- Error notes: show provider unavailable message if disabled

### `POST /api/v1/documents/upload`
- Purpose: upload + ingest PDF
- Request: `multipart/form-data`
  - `file`: PDF file (required)
  - `document_id`: string (optional)
- Response:
```json
{
  "document_id":"resume_123",
  "filename":"resume.pdf",
  "pages_processed":2,
  "chunks_created":8,
  "ingestion_timestamp":"2026-05-29T10:00:00+00:00",
  "duration_ms":482
}
```
- Frontend notes: show progress and ingest summary; refresh document list after success
- Error notes: handle `400/413/415/422` with specific UX copy

### `POST /api/v1/chat/query`
- Purpose: run RAG and get grounded answer + citations
- Request:
```json
{
  "query":"What does Newton's second law describe?",
  "top_k":3,
  "document_filter":"physics_notes",
  "conversation_id":"9d1606c7-9fc1-459c-b777-f5cd3f2b2e68"
}
```
- Response:
```json
{
  "answer":"Newton's second law states force equals mass times acceleration.",
  "citations":[
    {
      "filename":"physics_notes.pdf",
      "page_number":1,
      "chunk_id":"physics_notes_p1_c0",
      "snippet":"Newton's second law states force equals mass times acceleration."
    }
  ],
  "retrieval_debug":{
    "top_k":3,
    "total_latency_ms":131,
    "scores":[0.92,0.74],
    "chunk_ids":["physics_notes_p1_c0","physics_notes_p2_c0"],
    "citations_count":1
  }
}
```
- Frontend notes: render answer first, citations below; debug block hidden behind dev toggle
- Error notes: handle `403 forbidden_document`, `404 conversation_not_found`, `5xx` upstream failures

### `GET /api/v1/conversations`
- Purpose: list user conversations
- Response: array of `ConversationResponse`
- Frontend notes: sidebar data source

### `POST /api/v1/conversations`
- Purpose: create conversation
- Request:
```json
{"title":"Project Q&A"}
```
- Response: `ConversationResponse`

### `GET /api/v1/conversations/{conversation_id}`
- Purpose: conversation detail + messages
- Response: `ConversationDetailResponse`
- Frontend notes: hydrate message area from this endpoint

### `DELETE /api/v1/conversations/{conversation_id}`
- Purpose: delete conversation
- Response:
```json
{"ok":true}
```
- Frontend notes: optimistic remove from sidebar with rollback on failure

## 7) State Management Plan

### React Query (server state)
- `auth/me`
- conversations list/detail
- chat query mutations
- upload mutation + post-success invalidations
- health check

### Zustand (client app state)
- Auth UI state (isRefreshing, bootstrapComplete)
- Active conversation ID
- Draft message text
- Citation panel open/close + selected citation
- Upload queue UI state (if not fully mutation-local)
- Theme override state (if not using only CSS media/query)

### Local Storage
- Refresh token storage (or secure cookie if architecture updated)
- Non-sensitive preferences: theme, collapsed sidebar, last conversation id
- Never store access token long-term if avoidable; prefer memory + refresh strategy

### Suggested slices
- `authStore`: tokens, user, login/logout actions
- `chatStore`: activeConversationId, composer draft, streaming flags
- `uiStore`: theme, panel visibility, command palette, toasts

## 8) Design System

### Visual goals
- Premium
- Modern
- Minimal
- Excellent in both dark and light modes

### Inspiration references
- Linear (clarity + density)
- Vercel (typography + spacing discipline)
- Notion (information architecture)
- OpenAI (chat ergonomics)
- Perplexity (citation discoverability)

### Layout guidelines
- App shell: top nav + left sidebar + main content
- 12-column responsive grid for dashboard
- Chat view optimized for reading width, not full-bleed text
- Sticky composer with safe area spacing

### Typography
- Primary: `Geist` or `Söhne` equivalent
- Monospace: `JetBrains Mono` for metadata/debug
- Type scale: 12/14/16/20/24/32 with consistent line heights

### Color strategy
- Semantic tokens first: `bg`, `surface`, `text`, `muted`, `border`, `accent`, `danger`, `warning`, `success`
- Dark/light parity via CSS variables
- Citation highlights use neutral accent, not warning red

### Component principles
- Every async surface has empty/loading/error/success states
- Clear focus states and keyboard navigation
- Motion is subtle and purposeful (150-220ms transitions)
- Prefer composable primitives over one-off monolith components

## 9) Frontend Folder Structure (Next.js)

```text
src/
  app/
    (auth)/
      login/page.tsx
      signup/page.tsx
    (workspace)/
      dashboard/page.tsx
      upload/page.tsx
      chat/page.tsx
      settings/page.tsx
    api/
      auth/
      oauth/
    layout.tsx
    globals.css
  components/
    ui/
    layout/
    feedback/
  features/
    auth/
      components/
      hooks/
      schemas/
      services/
    dashboard/
    upload/
    chat/
    citations/
    settings/
  hooks/
    useAuthBootstrap.ts
    useTokenRefresh.ts
  services/
    api-client.ts
    endpoints/
      auth.ts
      documents.ts
      chat.ts
      conversations.ts
  stores/
    auth-store.ts
    chat-store.ts
    ui-store.ts
  types/
    api.ts
    auth.ts
    chat.ts
    documents.ts
  lib/
    env.ts
    utils.ts
    constants.ts
  providers/
    query-provider.tsx
    theme-provider.tsx
```

### Folder responsibilities
- `app/`: routes, layouts, page-level composition
- `components/`: shared presentational building blocks
- `features/`: domain modules with local components/hooks/services
- `hooks/`: cross-feature reusable hooks
- `services/`: API client and endpoint wrappers
- `stores/`: Zustand state containers
- `types/`: DTOs and shared type contracts
- `lib/`: foundational utilities and config
- `providers/`: app-level context providers

## 10) Development Roadmap (GitHub Issues)

### Issue #1: Authentication UI
Acceptance criteria:
- Login and signup pages implemented with validation.
- Auth errors mapped to user-friendly messages.
- Token storage + refresh workflow works.
- `/auth/me` bootstrap on app load.

### Issue #2: Dashboard
Acceptance criteria:
- Dashboard route protected behind auth.
- User profile card shown.
- Recent conversations section wired to `/conversations`.
- Uploaded documents section scaffolded (real list once endpoint finalized if needed).

### Issue #3: Upload Center
Acceptance criteria:
- Drag/drop and file picker support.
- Upload progress and completion summary.
- Correct handling for invalid mime, size, and empty/extraction errors.
- Success triggers dashboard/chat data refresh.

### Issue #4: Chat Workspace
Acceptance criteria:
- Query composer sends to `/chat/query`.
- Responses render answer + citations.
- Loading and error states implemented.
- Optional document filter supported in request.

### Issue #5: Conversation Sidebar
Acceptance criteria:
- List/create/delete conversations working.
- Selecting conversation loads details/messages.
- Active conversation state synchronized with URL or store.
- Empty state for new users.

### Issue #6: Citation Viewer
Acceptance criteria:
- Citation cards show filename/page/snippet/chunk id.
- Expand action opens detailed citation panel.
- Keyboard accessible interactions.
- Works in both light and dark mode.

### Issue #7: Settings Page
Acceptance criteria:
- Profile section wired to `/auth/me`.
- Security actions include logout.
- OAuth connection metadata displayed when present.
- Preference changes persist locally.

### Issue #8: Dark/Light Theme
Acceptance criteria:
- Theme toggle supports light/dark/system.
- Tokenized color variables applied globally.
- Contrast meets accessibility minimums.
- No visual regressions in chat/upload/dashboard flows.

## Implementation Notes and Assumptions
- API prefix is configured as `/api/v1` in backend settings.
- Core routes can be configured to require auth (`AUTH_REQUIRED_FOR_CORE_ROUTES`).
- OAuth providers may be disabled by env flags; frontend should detect and adapt.
- For production hardening, consider moving refresh tokens to `httpOnly` cookies behind a BFF layer.

## Recommended First Sprint Sequence
1. Issue #1 Authentication UI  
2. Issue #5 Conversation Sidebar  
3. Issue #4 Chat Workspace  
4. Issue #3 Upload Center  
5. Issue #2 Dashboard  
6. Issue #6 Citation Viewer  
7. Issue #8 Theme  
8. Issue #7 Settings

