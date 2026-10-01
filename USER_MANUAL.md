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

After adding sources, generate ideas based on them.

### Ideas Workspace

This is where the app turns your sources and strategy into draftable ideas.

Typical flow:

1. choose a source or input topic
2. generate ideas
3. review generated ideas
4. create content drafts from the chosen ideas

### Content Workspace

This is the main content production area.

You can:

- view all drafts
- filter by platform
- check quality scores
- edit draft bodies
- attach images
- approve, reject, or move drafts between review states
- schedule approved posts
- manually publish approved posts

#### Draft lifecycle

A typical content flow:

1. Idea created
2. Draft generated
3. Quality review performed
4. Draft submitted for review
5. Approved or rejected
6. Scheduled or manually published

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

This tab is intended for replying to conversations and drafting engagement responses.

Use it to:

- review inbox items
- prepare context-aware replies
- keep engagement aligned with brand voice

### Settings Workspace

This is where you manage account connections.

You can:

- connect LinkedIn
- connect X
- check OAuth status
- review callback results and errors

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

### Troubleshooting OAuth

If the connection fails, check:

- backend URL is correct
- frontend URL is correct
- the provider callback URL matches the backend route exactly
- the callback is not pointing to localhost when the app is deployed

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
