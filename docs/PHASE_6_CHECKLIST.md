# Phase 6: Conversational Layer — Verification Checklist

> Run through this checklist yourself AFTER Cursor says Phase 6 is complete.
> Every item must pass before moving to Phase 7.

---

## Docker & Infrastructure

- [ ] `docker-compose up --build` starts all services without errors
- [ ] All Phase 1-5 tests still pass
- [ ] Run: `docker-compose exec backend pytest app/tests/ -v`

---

## Chat Sidebar — Basic UI

- [ ] A floating chat button (icon) appears on every page of the app
- [ ] Clicking the button opens a chat sidebar from the right (~40% screen width)
- [ ] The rest of the app is still visible while chat is open
- [ ] Clicking the X button or the floating button again closes the sidebar
- [ ] Chat header shows "Ask your data" (or similar) and a conversation selector
- [ ] Input area at the bottom with text input and send button
- [ ] Enter sends the message, Shift+Enter adds a new line

---

## Suggested Questions

- [ ] When opening a new conversation (no messages yet), 4-5 suggested question chips appear
- [ ] Clicking a chip sends that question as the first message
- [ ] Chips disappear after the first message is sent
- [ ] Suggested questions are relevant (about priorities, segments, themes, etc.)

---

## Basic Conversation Flow

- [ ] Type "What are my top priorities?" and send
- [ ] A typing indicator appears while waiting for response
- [ ] An assistant response appears within 10 seconds (local Llama may be slower)
- [ ] The response mentions actual theme names from your data
- [ ] The response includes specific numbers (mention counts, priority scores)
- [ ] User messages appear right-aligned, assistant messages left-aligned

---

## RAG — Grounded Responses

- [ ] Ask "What are customers saying about [topic that exists in your feedback]?"
- [ ] The response quotes actual feedback from your data (not made up)
- [ ] The response references real customer names and segments (if matched)
- [ ] Ask about a topic that does NOT exist in your feedback
- [ ] The response says it doesn't have data on that topic (not hallucinated)

---

## Follow-Up Questions

- [ ] After getting a response about enterprise feedback, ask "How does that compare to SMB?"
- [ ] The response understands the context from the previous message
- [ ] Ask "Tell me more about that" — the response expands on the previous topic
- [ ] Ask 5+ follow-up questions in a row — conversation context is maintained throughout

---

## Tool Functions

Test each tool by asking questions that should trigger them:

### search_feedback
- [ ] "Show me feedback about authentication" → returns relevant feedback items

### get_theme
- [ ] "Tell me about the [theme name] theme" → returns theme details with stats and quotes

### list_themes
- [ ] "What are my top themes?" → returns ranked list of themes with scores

### compare_segments
- [ ] "Compare enterprise vs SMB feedback" → returns per-segment breakdown

### get_customer_feedback
- [ ] "What has [customer name] been saying?" → returns that customer's feedback

### get_stats
- [ ] "Give me an overview of my data" → returns total feedback, themes, customer counts

### filter_feedback
- [ ] "Show me critical urgency feedback from enterprise customers" → returns filtered results

---

## Conversation Management

- [ ] First message auto-generates a conversation title (visible in the dropdown)
- [ ] The title is meaningful (not "Conversation 1" but something like "Enterprise Auth Priorities")
- [ ] Click "New conversation" → starts a fresh conversation with suggested questions
- [ ] Switch between conversations using the dropdown → messages load correctly
- [ ] Old conversation messages are preserved when switching back
- [ ] Delete a conversation → it disappears from the list
- [ ] Deleted conversation's messages are no longer accessible

---

## Sources / Context Indicator

- [ ] Each assistant response shows a small "Sources" indicator
- [ ] It shows something like "Based on X feedback items, Y themes"
- [ ] Expanding it shows which feedback items and themes were used
- [ ] This helps the PM verify the response is grounded in real data

---

## Page-Aware Context

- [ ] Navigate to a Theme Detail page → open chat → ask "Tell me about this theme"
- [ ] The response correctly references the theme you're viewing
- [ ] Navigate to a Customer page → open chat → ask "What are they saying?"
- [ ] The response correctly references that customer's feedback
- [ ] Navigate to the Feedback list (no specific context) → ask a general question
- [ ] The response works normally without page context

---

## Markdown Rendering

- [ ] Assistant responses render bold text correctly
- [ ] Lists in responses render as actual lists
- [ ] Quoted feedback appears in styled callout blocks
- [ ] Theme names in responses are clickable (link to theme detail)

---

## Multi-Tenant Isolation

- [ ] Create a second org with different feedback
- [ ] Log in as the second org user
- [ ] Chat only references the second org's data (not the first org's)
- [ ] The first org's conversations are not visible to the second org

---

## Per-User Isolation

- [ ] If your org has two users, each user's conversations are separate
- [ ] User A cannot see User B's conversation list
- [ ] User A cannot access User B's conversation messages by guessing the ID

---

## Performance

- [ ] First response time: under 10 seconds (local Llama) or under 5 seconds (Claude API)
- [ ] Follow-up responses: similar speed
- [ ] Chat doesn't slow down other parts of the app
- [ ] Long conversations (20+ messages) still respond within acceptable time

---

## Error Handling

- [ ] If the LLM is down, the chat shows a user-friendly error ("Something went wrong, please try again")
- [ ] If embedding generation fails, the chat still works (falls back to tool-based queries)
- [ ] Sending an empty message is blocked (input validation)
- [ ] Very long messages (5000+ chars) are handled gracefully

---

## Quick API Spot Checks

Open `http://localhost:8000/docs` and test:

- [ ] `POST /api/v1/chat/send` — sends message, returns response
- [ ] `GET /api/v1/chat/conversations` — returns user's conversations
- [ ] `GET /api/v1/chat/conversations/{id}/messages` — returns messages
- [ ] `DELETE /api/v1/chat/conversations/{id}` — soft deletes
- [ ] All error responses follow: `{ "error": { "code": "...", "message": "..." } }`

---

## Tests

- [ ] All Phase 6 backend tests pass
- [ ] All Phase 5 backend tests still pass
- [ ] All Phase 4 backend tests still pass
- [ ] All Phase 3 backend tests still pass
- [ ] All Phase 2 backend tests still pass
- [ ] All Phase 1 backend tests still pass
- [ ] Run: `docker-compose exec backend pytest app/tests/ -v`

---

## The "Is It Actually Useful?" Test

This is the most important test. Forget the checkboxes:

1. Open the chat sidebar.
2. Pretend you're a PM who just ingested 200 feedback items and clustered them.
3. Ask: "What should I focus on this week?"
4. Does the answer reference your actual top-priority themes?
5. Ask: "Why is [top theme] the highest priority?"
6. Does it explain the score breakdown (volume, reach, urgency, etc.)?
7. Ask: "What are enterprise customers most frustrated about?"
8. Does it give specific examples with real quotes?
9. Ask: "How does that compare to what SMB customers are saying?"
10. Does it give a meaningful comparison?

If you feel like the chat is giving you real insights about your data — not generic fluff — Phase 6 is done.

---

## If Something Fails

Tell Cursor: "Phase 6 checklist item [X] failed. Here's what happened: [describe]. Fix it following the spec in docs/PHASE_6_SPEC.md."

Once everything passes, move to Phase 7.
