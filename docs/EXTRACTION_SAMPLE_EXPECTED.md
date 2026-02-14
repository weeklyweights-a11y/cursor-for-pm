# Extraction: Sample Feedback → Expected Categories

This doc maps the sample CSV and manual feedback to the categories the extractor uses (topic, urgency, sentiment, etc.) so you can compare with actual extraction results.

## Validation rules (what the extractor accepts)

- **topic**: Non-empty string (e.g. performance, search, onboarding, pricing, mobile).
- **urgency**: Exactly one of `low` | `medium` | `high` | `critical` (lowercase).
- **sentiment**: Exactly one of `positive` | `neutral` | `negative` (lowercase).
- **is_existing_feature**: Boolean (true/false).
- **confidence**: Number 0.0–1.0 (optional; default 0 if missing).
- **pain_point**, **verbatim_quote**, **related_feature**, **feature_gap**: Strings (optional except pain_point).

---

## Sample CSV (`feedback_small.csv`) → Expected mapping

| # | Feedback (short) | Expected topic | Expected urgency | Expected sentiment |
|---|------------------|----------------|------------------|---------------------|
| 1 | Dashboard slow, 50+ widgets, pagination | performance | high | negative |
| 2 | Love export to PDF, saves an hour | export / features | low | positive |
| 3 | Cannot delete project with archived items | bugs / projects | medium | negative |
| 4 | Feature request: dark mode for editor | feature request / UI | medium | neutral |
| 5 | Bulk editing, 200+ items | productivity / features | high | neutral |
| 6 | Login fails on Safari, works Chrome | authentication | high | negative |
| 7 | Onboarding too long, lost 3 users | onboarding | high | negative |
| 8 | API rate limit too low, need 1000/min | API / integrations | high | negative |
| 9 | Great customer support, under an hour | support | low | positive |
| 10 | Mobile app crashes, notifications, Android 14 | mobile / notifications | high | negative |
| 11 | Keyboard shortcuts in roadmap | UX / feature request | low | neutral |
| 12 | Search not return last 7 days, cache bug | search / bugs | high | negative |
| 13 | Pricing unclear, which plan has SSO | pricing | medium | negative |
| 14 | Export Excel missing custom columns | export | medium | negative |
| 15 | Slack notification when task assigned | integrations / notifications | medium | neutral |

---

## Manual feedback samples (`manual_feedback_samples.txt`) → Expected mapping

| Feedback (short) | Expected topic | Expected urgency | Expected sentiment |
|------------------|----------------|------------------|---------------------|
| Checkout confusing, users abandon step 2 | checkout / UX | high | negative |
| Dark mode for dashboard | feature request / UI | medium | neutral |
| Notifications don't appear on mobile in background | mobile / notifications | high | negative |
| Export reports to PDF, currently only CSV | export | medium | neutral |
| New search much faster | search | low | positive |
| Login with Google would save support tickets | authentication | medium | neutral |
| Page refresh loses draft, very frustrating | bugs / UX | high | negative |
| Bulk delete option for old items | feature request | medium | neutral |

---

## Why extractions were failing (and what was fixed)

1. **Urgency/sentiment casing** – Model sometimes returned `"High"` or `"Negative"`. Validation expects lowercase. **Fix:** Normalize to lowercase before validation.
2. **is_existing_feature as string** – Model sometimes returned `"true"`/`"false"` (string). Validation expects Python bool. **Fix:** Normalize string/1/0 to bool.
3. **Missing confidence** – Model sometimes omitted `confidence`. **Fix:** Treat confidence as optional in validation; default 0 when saving.

After normalization, re-run extraction for failed items via **POST /api/v1/feedback/extract-pending** (enqueues all pending + failed).
