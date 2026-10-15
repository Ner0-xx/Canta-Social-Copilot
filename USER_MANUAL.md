# Canta Social Copilot User Manual

## 1. Overview

Canta Social Copilot is an AI-assisted workspace for planning, drafting, reviewing, scheduling, and analyzing social content for X and LinkedIn.

The workflow is designed to keep a human in the loop:

- research and collect sources
- generate ideas and drafts
- review quality and safety warnings
- approve or reject content
- schedule or publish manually
- review analytics and experiments

---

## 2. Getting Started

### Sign in

1. Open the frontend app.
2. Sign in with your Supabase-supported account.
3. After sign-in, the main workspace tabs will become available.

### Required accounts and services

Before using the app fully, make sure you have:

- a Supabase project
- a Groq API key
- a LinkedIn OAuth app configured, if you want LinkedIn connection
- an X OAuth app configured, if you want X connection
- a backend running locally or on Render

---

## 3. Main Workspace Tabs

### Overview Workspace

Overview is the app’s home screen and daily command center. It brings together:

- LinkedIn and X connection status and the connected account names
- draft counts for review, approved posts, upcoming scheduled posts, and published posts
- the next pending scheduled posts and a link to the full calendar
- a heads-up when drafts have unresolved quality warnings
- shortcuts to create a post, explore ideas, and add a source

Use Refresh to check the latest workspace data. If a section cannot load, Overview marks that data unavailable rather than treating a failed request as an empty list. Provider access may be expired even when an account is connected; reconnect or refresh access from Settings if publishing is blocked.

### Strategy Workspace

Use this tab to define your brand profile and content rules.

Typical values include:

- brand name and purpose
- audience segments
- content pillars
- tone and vocabulary rules
- offer and disclosure guidance

This information is used as context for idea generation and post drafting.

### Sources Workspace

Use this tab to add content sources that can inform idea generation.

Supported sources may include:

- RSS feeds
- URLs
- notes or documents
- reference content for trend research

After adding a source, Canta immediately tries to ingest it. RSS feeds, web pages, and notes are also synchronized automatically when the backend starts and every 24 hours afterward. Each source displays its last successful sync time; use **Sync** to fetch it sooner. If one source fails during the scheduled run, the others are still processed, and the failed source is marked with an error for the next daily retry.

Use **Delete** to remove a source and its ingested items. Ideas and drafts already created from that material are kept. Deletion cannot be undone.

### How sources are used

- RSS sources provide up to 10 feed items per sync.
- Web-page sources provide the page title and extracted text.
- Notes are saved as source material for idea generation.
- Ingested material appears in the Sources inbox and can be selected in Ideas. The selected item's title and content are sent to the configured AI provider as context for generating content ideas; your saved Strategy and available performance context are also used.
- Generated ideas are saved in the app. Choosing an idea and generating drafts produces platform-specific draft variants that you can review and edit before approval.

Adding or syncing a source does not itself publish anything to a social account.

### Ideas Workspace

This is where the app turns your sources and strategy into draftable ideas.

Typical flow:

1. choose a source or input topic
2. ask the configured AI provider to generate five distinct, source-grounded ideas
3. review generated ideas
4. create content drafts from the chosen ideas

Idea and draft generation require a supported AI provider to be configured on the backend. If the provider is unavailable or returns an invalid response, the app reports the problem instead of substituting template content. Selecting **Generate X & LinkedIn Drafts** makes a separate AI request to develop the selected idea into an X post, X thread, and LinkedIn post. If that request fails, no drafts are created and the idea remains available to retry. Use **Remove** to archive an unwanted idea from the inbox; any drafts already created from it are preserved.

### Content Workspace

This is the main content production area.

You can:

- view all drafts
- permanently delete unpublished drafts that are no longer needed
- filter by platform
- check quality scores
- edit draft bodies
- attach images
- approve, reject, or move drafts between review states
- schedule approved posts
- publish approved posts to the connected X or LinkedIn account
- manually publish an X draft on X and record its post link when using the secondary fallback

**Deleting drafts:** Use **Delete draft** on an unpublished draft you no longer need. A confirmation appears before deletion. Drafts with a pending schedule or publication record cannot be deleted. A draft whose schedule was cancelled can be deleted; the cancellation audit event is retained.

#### Draft lifecycle

A typical content flow:

1. Idea created
2. Draft generated
3. Quality review performed
4. Draft submitted for review
5. Approved or rejected
6. Scheduled or manually published

**Publishing requirements:** manual publishing uses the connected provider’s official API; it does not merely mark a draft as published. The app must have the corresponding account connected, the draft must be approved, the release level must be **Integrate** (or higher), and **Publishing enabled** must be on. A provider error leaves the draft approved so you can correct the issue and retry. Scheduled publishing also uses the official provider publishing services.

**Manual X fallback:** for an approved X draft, use **Open X to post** and copy the draft text from Canta. After publishing directly on X, select **I posted this on X**, paste the X post URL, and confirm. Canta records the post URL against the draft and marks it published as **Manually confirmed**; this is your confirmation and is not independently verified with X. Manual confirmation still requires **Publishing enabled** and a release level of **Approve** or higher. The normal **Publish via X API** action remains available and continues to publish through X when API access is working.

Manually confirmed X posts appear in Analytics with a link to the post. Enter and save their views, likes, comments, and reposts there. Metrics are user-entered, not fetched or verified by X.

#### Quality check

When a draft is selected, use the quality check feature to review warnings such as:

- unsafe or unclear claims
- weak originality
- policy issues
- repetitive language

### Analytics Workspace

This tab shows dashboard metrics and reports.

You can:

- review top-performing posts
- import analytics CSV files
- manually log recent X post metrics
- track experiments and performance comparisons

### Engagement Workspace

The Engagement tab fetches up to 20 recent posts and up to 20 recent mentions for the connected X account from X’s user-post and mentions endpoints. Use Refresh to fetch current provider data. Mentions are posts that mention the X account; this is not a complete feed of every comment on all of your posts. AI replies are drafts for review and copying; this screen does not publish replies.

LinkedIn feed and inbox reading are not available with the current app permissions. The Engagement tab explains this limitation instead of showing sample conversations. LinkedIn post publishing remains supported through the Content workspace.

### X Inbox

The separate X Inbox tab fetches and groups Direct Message events from X. The view is read-only and requests the `dm.read` OAuth scope. X limits this endpoint to a recent event history (up to 30 days); this app requests up to the latest 100 message events per refresh, so older conversations or messages may not appear. Availability also depends on the X account’s permissions, developer-project configuration, and API access tier. A 403 response means X denied the request; it does not mean the inbox is empty.

### Settings Workspace

This is where you manage account connections.

You can:

- connect or disconnect LinkedIn and X individually
- see a clear connected/not-connected badge and the connected account name
- check OAuth status and access-token expiry
- review callback results and errors

Disconnecting removes that platform's saved connection from this app; it does not delete or change your social account.

---

## 4. Connecting LinkedIn and X

### Important requirement

The OAuth callback URLs depend on the deployed or local backend URL.

The backend must know its own public URL using:

- `BACKEND_BASE_URL` in the backend environment
- `FRONTEND_ORIGIN` in the backend environment

If you are running locally, this is usually:

- `BACKEND_BASE_URL=http://127.0.0.1:8000`
- `FRONTEND_ORIGIN=http://127.0.0.1:5173`

If you are deployed, use your Render and Vercel URLs instead.

### Connection flow

1. Go to Settings.
2. Click the platform connection button.
3. The app redirects to the provider login flow.
4. Return to the app after authorization.
5. The callback completes the OAuth token exchange.
6. The connection status should switch to connected.

After deploying live X Engagement and Inbox support, reconnect X once and approve the newly requested `dm.read` scope. The existing X connection will not receive this permission until the OAuth consent flow is completed again. The app does not request `dm.write` because the inbox is view-only.

### Troubleshooting OAuth

If the connection fails, check:

- backend URL is correct
- frontend URL is correct
- the provider callback URL matches the backend route exactly
- the callback is not pointing to localhost when the app is deployed

### Keeping the X connection active

X access tokens expire, but the app can refresh them when X has issued a refresh token:

- The backend automatically refreshes X credentials shortly before a scheduled publish if they are near expiry.
- If Settings reports an expired X access token, use **Refresh access** when available.
- If the refresh token is unavailable or expired, reconnect X and approve the `offline.access` permission.

Before deploying this feature, set `X_REFRESH_TOKEN_ENCRYPTION_KEY` in the backend environment. Generate one with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`, store it securely, and keep it unchanged for as long as encrypted tokens are stored. Apply the database migration from the `backend` directory using `alembic upgrade head` before starting the new backend version. Reconnect X once after deployment; existing connections cannot provide a refresh token retroactively.

---

## 5. Using the Content Workflow

### Example workflow

1. Set your brand strategy.
2. Add a source or content topic.
3. Generate ideas.
4. Select an idea and generate drafts.
5. Edit the draft if needed.
6. Submit the draft for review.
7. Approve it when satisfied.
8. Schedule it or manually publish it.
9. Review the analytics afterward.

---

## 6. Scheduling and Publishing

### Scheduling

Approved drafts can be scheduled for a chosen date and time.

Use the schedule field in the Content Workspace and choose the exact date/time.

### Manual Publishing

For some platforms, you may choose manual publish instead of scheduling.

This is useful when:

- you want final human review
- you are testing a post before wider release
- your platform access is partially limited

---

## 7. Analytics and Experiments

The analytics area helps you understand what is working.

Use it to:

- view impressions and engagement totals
- inspect top-performing content
- import analytics CSV files
- log recent X metrics manually
- compare experiment variants

This lets the app learn from what has already performed well and inform future content decisions.

---

## 8. Best Practices

- keep your strategy profile updated
- review quality warnings before approval
- avoid publishing without human approval
- validate OAuth URLs before deploying
- use realistic source material and avoid low-quality content inputs
- keep platform-specific tone and audience in mind for every draft

---

## 9. Troubleshooting

### App does not load

Check:

- frontend dependencies installed
- backend server running
- API URL points to the correct backend

### OAuth redirect fails

Check:

- backend is running on the correct URL
- callback URL matches provider settings
- frontend origin is correct in backend config

### Analytics data looks empty

Check:

- CSV import was successful
- recent posts exist in the source data
- the backend API is reachable from the frontend

### Quality warnings are excessive

Review the draft and adjust:

- tone and wording
- factual claims
- references and source quality
- unsupported statements

---

## 10. Quick Start Summary

If you want the shortest path:

1. set up Supabase
2. set up Groq
3. run backend locally or deploy it
4. run frontend locally or deploy it
5. set strategy
6. add sources
7. generate ideas
8. create and review drafts
9. connect LinkedIn/X
10. schedule or publish approved content
11. monitor analytics

---

## 11. Support and Maintenance

This project is intended to operate as a human-approved content system.

Use the app as a drafting and decision-support tool, not as an autonomous publisher.

For any production deployment, validate the live callback URLs, OAuth configuration, and environment variables before launching the app for real users.
