# Phase 6: Conversational Layer

> **Goal:** PMs can ask questions about their data in natural language. A chat sidebar lets the PM explore their feedback, themes, customers, and priorities conversationally. The system uses RAG (retrieval augmented generation) — searches embeddings for relevant feedback, pulls in theme and customer data, and sends context to the LLM to produce grounded, evidence-backed answers.
>
> **Done means:** A PM opens the chat sidebar and types "What are enterprise customers most frustrated about?" The system searches their feedback embeddings, finds relevant items, pulls in matched customer and theme data, sends it all as context to the LLM, and responds with a specific, evidence-backed answer citing real feedback quotes and theme names. The PM can follow up: "How does that compare to SMB customers?" and get a contextual response. Conversation history is stored per user.

---

## Context for the AI Agent

This is Phase 6 of 8. Phases 1-5 are complete — you have authentication, feedback ingestion, LLM extraction, customer enrichment with smart matching, pgvector embeddings, HDBSCAN clustering into themes, and a 5-factor prioritization engine with ranked theme dashboard.

This phase adds the conversational interface. The PM can now TALK to their data instead of just looking at dashboards. This is a major UX upgrade — it turns the product from a reporting tool into an interactive analyst.

Read `.cursorrules` before starting. All rules apply.

**Project root:** `D:\LinkedIn\Week4`

---

## What You Are Building

Three things:

1. **Chat interface** — A slide-out sidebar on the right side of the app. PM types questions, gets responses. Conversation persists within a session and across sessions (stored in DB).

2. **RAG pipeline** — When the PM asks a question, the system: (a) generates an embedding for the question, (b) searches feedback items by vector similarity, (c) gathers relevant theme and customer context, (d) sends everything to the LLM with a system prompt, (e) streams the response back.

3. **Tool functions** — The LLM can "call" predefined tool functions to query structured data: filter feedback by segment, get theme details, compare segments, get top customers, get priority scores. This makes the chat smart about structured queries, not just semantic search.

---

## New Dependencies

| Package | Purpose |
|---------|---------|
| (none new) | Uses existing: sentence-transformers for embeddings, LLM service for chat, SQLAlchemy for queries, pgvector for similarity search |

---

## Database Changes

### New Table: conversations

Stores chat sessions per user.

| Column | Type | Rules |
|--------|------|-------|
| id | UUID (PK) | Auto-generated |
| org_id | UUID (FK to organizations) | Required, indexed |
| user_id | UUID (FK to users) | Required, indexed |
| title | string, max 255 | Nullable. Auto-generated from first message or set by user. |
| is_active | boolean | Default true. False for archived conversations. |
| created_at | timestamptz | Auto-generated |
| updated_at | timestamptz | Auto-generated |

**Index:** (org_id, user_id) composite for listing a user's conversations.

### New Table: messages

Individual messages within a conversation.

| Column | Type | Rules |
|--------|------|-------|
| id | UUID (PK) | Auto-generated |
| conversation_id | UUID (FK to conversations) | Required, indexed |
| org_id | UUID (FK to organizations) | Required, indexed |
| role | string (enum: user, assistant, system) | Required. Who sent this message. |
| content | text | Required. The message text. |
| context_used | JSONB | Nullable. For assistant messages: metadata about what RAG context was used (feedback_item_ids, theme_ids, search query, tool calls). For debugging and transparency. |
| tool_calls | JSONB | Nullable. If the LLM used tool functions, store which ones and their results. |
| tokens_used | integer | Nullable. Approximate token count for this exchange. |
| duration_ms | integer | Nullable. How long the LLM took to respond. |
| created_at | timestamptz | Auto-generated |

**Index:** (conversation_id, created_at) for loading messages in order.

---

## RAG Pipeline

### How It Works (Step by Step)

When the PM sends a message:

1. **Load conversation history.** Get the last N messages (default 20) from this conversation. These provide context for follow-up questions.

2. **Classify the query.** Determine what kind of question this is:
   - **Semantic search:** "What are customers saying about search?" → needs embedding search
   - **Structured query:** "How many critical bugs from enterprise?" → needs database query via tool function
   - **Comparison:** "Compare enterprise vs SMB feedback on onboarding" → needs filtered queries + comparison
   - **Theme question:** "Tell me about the SSO theme" → needs theme lookup
   - **General/meta:** "What should I focus on this week?" → needs theme priorities + context
   - **Follow-up:** "Tell me more about that" → needs conversation history for context

   The classification happens implicitly — send the query + available tool descriptions to the LLM, and let the LLM decide whether to use tools or rely on provided context.

3. **Generate query embedding.** Use the same sentence-transformers model (all-MiniLM-L6-v2) to embed the PM's question.

4. **Retrieve relevant feedback.** Use pgvector cosine similarity to find the top 20 most relevant feedback items for this org. Filter out items without embeddings.

5. **Enrich retrieved context.** For each retrieved feedback item, include:
   - The feedback content (truncated to 200 chars)
   - Pain point
   - Topic
   - Urgency
   - Sentiment
   - Customer name and segment (if matched)
   - Theme name (if assigned)
   - Verbatim quote

6. **Add structured context.** Also include:
   - Top 5 current themes with names, mention counts, and priority scores
   - The PM's product context (name, description)
   - Total feedback count, extraction stats, enrichment stats

7. **Build the LLM prompt.** Combine:
   - System prompt (defines the assistant's role and available tools)
   - Conversation history (last N messages)
   - Retrieved context (relevant feedback items, themes, stats)
   - The PM's new question

8. **Call the LLM.** Send the complete prompt. Use Claude Sonnet (or Llama 3.2 locally) — this needs a smarter model than extraction because it's having a conversation.

9. **Parse the response.** If the LLM used tool functions, execute them and send results back to the LLM for a final answer. If not, return the text response directly.

10. **Store everything.** Save the user message and assistant response in the messages table. Include context_used metadata for debugging.

### What the System Prompt Says

The system prompt defines the chat assistant's personality and capabilities:

```
You are an AI product analyst assistant. You help product managers understand their customer feedback data and make evidence-based decisions.

You have access to the PM's feedback data, customer information, themes (clusters of similar feedback), and priority scores.

Rules:
- Always ground your answers in actual data. Cite specific feedback quotes, theme names, and numbers.
- If you don't have enough data to answer confidently, say so.
- Never make up feedback or quotes that aren't in the provided context.
- When discussing priorities, reference the scoring factors (volume, reach, urgency, sentiment, strategic fit).
- Keep responses concise but thorough. Use specific numbers and examples.
- If the PM asks about something outside their data, redirect to what you can help with.
```

Store this prompt template in `backend/app/prompts/chat.py`.

---

## Tool Functions

The LLM can call these functions to query structured data. Implement them as callable functions that the LLM can invoke via function calling (for Anthropic) or as a tool-use pattern (for Ollama, simulate with prompt-based tool use).

### Available Tools

| Tool Name | Description | Parameters | Returns |
|-----------|-------------|------------|---------|
| `search_feedback` | Search feedback by text similarity | query (string), limit (int, default 10), segment (optional), urgency (optional), source_type (optional) | List of matching feedback items with all fields |
| `get_theme` | Get a specific theme's details | theme_name (string) or theme_id (string) | Theme with full stats, score breakdown, top quotes |
| `list_themes` | Get all current themes ranked by priority | sort_by (optional: priority_score, mention_count, urgency), limit (int, default 10) | Ranked list of themes with scores |
| `compare_segments` | Compare feedback across customer segments | segments (list of strings), topic (optional) | Per-segment stats: count, top themes, urgency breakdown, sentiment breakdown |
| `get_customer_feedback` | Get feedback for a specific customer | customer_name (string) or customer_id (string), limit (int, default 10) | Customer info + their feedback items |
| `get_stats` | Get overall dashboard statistics | (none) | Total feedback, by source, by status, themes count, top customers, extraction/enrichment stats |
| `filter_feedback` | Filter feedback by multiple criteria | segment (optional), urgency (optional), sentiment (optional), theme (optional), source_type (optional), date_from (optional), date_to (optional), limit (int, default 20) | Filtered feedback items |

### How Tool Calling Works

**For Anthropic (production):** Use Claude's native tool use / function calling. Define tools in the API call. Claude decides when to use them and returns tool_use blocks. Execute the function, send results back, get final answer.

**For Ollama (local dev):** Llama 3.2 3B has limited tool-calling ability. Use a simpler approach: include tool descriptions in the system prompt. Ask the model to respond with JSON if it wants to use a tool: `{ "tool": "search_feedback", "params": { "query": "SSO" } }`. Parse the response, detect tool calls, execute, and re-prompt with results.

**Important:** The tool calling logic must be in a separate service (`tool_service.py`), not embedded in the chat route or LLM service. Each tool function maps to a service call that queries the database.

### Tool Execution Flow

1. LLM receives the prompt with tool definitions.
2. LLM decides to call a tool (e.g., `compare_segments(["enterprise", "smb"], "onboarding")`).
3. System executes the tool function against the database.
4. System sends the tool result back to the LLM.
5. LLM generates a final response incorporating the tool result.
6. System returns the response to the PM.

Maximum tool calls per turn: 3. If the LLM tries to call more, stop and generate a response with what it has. This prevents infinite loops.

---

## Services

### chat_service.py

The main orchestrator for chat. This is the most complex service in this phase.

Functions:
- `send_message(db, org_id, user_id, conversation_id, content)` — Full RAG pipeline: load history, generate embedding, retrieve context, build prompt, call LLM (with tool loop if needed), store messages, return response.
- `create_conversation(db, org_id, user_id, title)` — Create a new conversation. If title is null, auto-generate from first message later.
- `get_conversations(db, org_id, user_id, page, page_size)` — List user's conversations, most recent first.
- `get_conversation_messages(db, org_id, user_id, conversation_id, page, page_size)` — Load messages for a conversation. Paginated, oldest first.
- `delete_conversation(db, org_id, user_id, conversation_id)` — Soft delete (set is_active=false).
- `build_rag_context(db, org_id, query_embedding, query_text)` — Retrieve relevant feedback via pgvector, enrich with theme/customer data, format as context string.
- `build_chat_prompt(system_prompt, conversation_history, rag_context, user_message, tools)` — Assemble the complete prompt for the LLM.
- `auto_title_conversation(db, conversation_id, first_message)` — Use LLM to generate a short title (3-6 words) from the first message.

### tool_service.py

Executes tool functions called by the LLM.

Functions:
- `execute_tool(db, org_id, tool_name, params)` — Route to the correct tool function. Return results as a dict.
- `search_feedback_tool(db, org_id, query, limit, filters)` — Embed the query, search via pgvector, apply filters, return results.
- `get_theme_tool(db, org_id, theme_name_or_id)` — Look up theme by name (fuzzy) or ID.
- `list_themes_tool(db, org_id, sort_by, limit)` — Return ranked themes.
- `compare_segments_tool(db, org_id, segments, topic)` — Query feedback grouped by segment, compute per-segment stats.
- `get_customer_feedback_tool(db, org_id, customer_name_or_id, limit)` — Look up customer, return their feedback.
- `get_stats_tool(db, org_id)` — Aggregate dashboard stats.
- `filter_feedback_tool(db, org_id, filters)` — Multi-criteria feedback filter.
- `get_tool_definitions()` — Return the tool schema for the LLM prompt (tool names, descriptions, parameter schemas).

### rag_service.py

Handles the retrieval part of RAG.

Functions:
- `retrieve_relevant_feedback(db, org_id, query_embedding, limit, filters)` — pgvector similarity search with optional filters (segment, urgency, etc.). Returns feedback items ordered by relevance.
- `format_feedback_context(feedback_items)` — Format retrieved items into a concise string for the LLM context window. Truncate content, include key fields.
- `format_theme_context(themes)` — Format top themes into context string.
- `format_stats_context(db, org_id)` — Generate a summary stats string.
- `estimate_token_count(text)` — Rough token estimate (chars / 4). Used to ensure context fits within limits.
- `truncate_context(context, max_tokens)` — If context exceeds max_tokens, trim oldest/least relevant items.

---

## Context Window Management

The LLM has a limited context window. You need to manage what goes in:

| Component | Approximate Tokens | Priority |
|-----------|-------------------|----------|
| System prompt | ~300 | Always included |
| Conversation history (last 20 messages) | ~2000-4000 | Always included, truncate oldest if too long |
| RAG context (top 20 feedback items) | ~3000-5000 | Always included, reduce count if needed |
| Theme summary (top 5 themes) | ~500 | Always included |
| Stats summary | ~200 | Always included |
| Tool definitions | ~800 | Always included |
| User's new message | ~100-500 | Always included |
| **Total budget** | **~12000** | Leave room for response (~4000 tokens) |

**If context exceeds budget:**
1. Reduce conversation history to last 10 messages.
2. Reduce RAG feedback items to top 10.
3. Reduce theme summary to top 3.
4. If still over, truncate feedback content more aggressively.

Use the `estimate_token_count` function to check before sending.

---

## LLM Configuration for Chat

Chat uses a different model configuration than extraction:

| Setting | Dev (Ollama) | Production (Anthropic) |
|---------|-------------|----------------------|
| Model | llama3.2:3b | claude-sonnet-4-20250514 |
| Temperature | 0.3 | 0.3 |
| Max tokens (response) | 1500 | 2000 |
| Timeout | 60 seconds | 30 seconds |

**Why Sonnet instead of Haiku for chat?** Chat requires reasoning about data, following conversation context, deciding when to use tools, and generating nuanced analytical responses. Haiku is great for extraction (structured, predictable output) but chat needs a smarter model. The cost difference is small because chat volume is low (PMs ask a few questions per session, not hundreds).

**New environment variables:**

| Variable | Dev Value | Prod Value | Purpose |
|----------|-----------|------------|---------|
| CHAT_LLM_MODEL | llama3.2:3b | claude-sonnet-4-20250514 | Model for chat (separate from extraction) |
| CHAT_MAX_HISTORY | 20 | 20 | Max conversation messages to include |
| CHAT_MAX_RAG_ITEMS | 20 | 20 | Max feedback items to retrieve |
| CHAT_MAX_RESPONSE_TOKENS | 1500 | 2000 | Max tokens for LLM response |
| CHAT_TEMPERATURE | 0.3 | 0.3 | LLM temperature for chat |

---

## Tasks (Celery)

### tasks/chat_tasks.py

- `auto_title_task(conversation_id, first_message)` — Generate conversation title from first message. Runs async so the PM doesn't wait.

No other Celery tasks needed — chat is synchronous (PM sends message, waits for response). The response time target is under 5 seconds.

---

## Schemas (Pydantic)

### schemas/chat.py

- `SendMessageRequest` — content (required string), conversation_id (optional UUID — if null, create new conversation).
- `MessageResponse` — id, conversation_id, role, content, context_used (optional), tool_calls (optional), created_at.
- `ConversationResponse` — id, title, is_active, message_count, last_message_at, created_at.
- `ConversationListResponse` — Paginated list of conversations.
- `ConversationMessagesResponse` — Paginated list of messages for a conversation.
- `ChatResponse` — The response to a send_message call: the assistant's message + conversation_id (for new conversations).

---

## Models (SQLAlchemy)

### New Models

- `backend/app/models/conversation.py` — Conversation model.
- `backend/app/models/message.py` — Message model.

Update models `__init__.py` to export new models.

---

## Alembic Migrations

**`009_create_conversations_and_messages`** — Create both tables with all columns, indexes, and foreign keys.

---

## API Endpoints

### Chat

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/v1/chat/send | Yes | Send a message. Returns assistant response. Creates new conversation if no conversation_id provided. |
| GET | /api/v1/chat/conversations | Yes | List user's conversations. Paginated, most recent first. |
| GET | /api/v1/chat/conversations/{id}/messages | Yes | Get messages for a conversation. Paginated, oldest first. |
| DELETE | /api/v1/chat/conversations/{id} | Yes | Soft delete a conversation. |
| POST | /api/v1/chat/conversations/{id}/clear | Yes | Clear all messages in a conversation (keep the conversation). |

### Response Shape for POST /chat/send

```
{
  "data": {
    "message": {
      "id": "uuid",
      "role": "assistant",
      "content": "Based on your data, enterprise customers are most frustrated about...",
      "context_used": {
        "feedback_items_searched": 20,
        "feedback_items_relevant": 8,
        "themes_referenced": ["SSO & Enterprise Auth", "Search Performance"],
        "tools_called": ["compare_segments"],
        "query_embedding_generated": true
      },
      "created_at": "2026-02-12T..."
    },
    "conversation_id": "uuid"
  }
}
```

---

## Frontend Changes

### Chat Sidebar (NEW — the main deliverable)

A slide-out panel on the right side of the app. Available on every page.

**Trigger:** A floating "Ask" button (or chat icon) in the bottom-right corner. Clicking it slides the chat panel open from the right. The panel takes up ~40% of the screen width. The rest of the app is still visible and usable.

**Chat Panel Layout:**
- **Header:** "Ask your data" title. Conversation selector dropdown (switch between conversations). "New conversation" button. Close button (X).
- **Messages area:** Scrollable list of messages. User messages right-aligned, assistant messages left-aligned. Assistant messages can contain markdown (bold, lists, quotes). Show a typing indicator while waiting for response.
- **Input area:** Text input at the bottom. Send button. Enter to send, Shift+Enter for new line.

**Message Formatting:**
- Assistant messages render markdown.
- Feedback quotes in assistant responses are styled as callout blocks.
- Theme names in responses are clickable — clicking navigates to the theme detail page.
- Customer names in responses are clickable — clicking navigates to the customer detail.
- Numbers and stats are formatted nicely.

**Suggested Questions:**
When the conversation is empty (first message), show 4-5 suggested questions as clickable chips:
- "What are my top priorities this week?"
- "What are enterprise customers most frustrated about?"
- "Compare feedback from enterprise vs SMB"
- "What themes have the highest urgency?"
- "Show me recent critical feedback"

Clicking a chip sends that question as the first message.

**Conversation Management:**
- Conversations are listed in the dropdown by title (auto-generated) and date.
- PM can switch between conversations.
- PM can start a new conversation.
- PM can delete old conversations.

### Chat Context Indicator

When the assistant responds, show a small collapsible "Sources" section below the message:
- "Based on X feedback items, Y themes"
- Expandable to show the specific feedback items and themes referenced.
- This builds trust — the PM can verify the answer.

### Page-Aware Context

The chat should be aware of what page the PM is on:
- On the Theme Detail page → automatically include that theme as context.
- On the Feedback Detail page → automatically include that feedback item as context.
- On the Customer Detail page → automatically include that customer as context.

Pass the current page context to the chat API as an optional field in SendMessageRequest:
- `page_context` (optional JSONB): `{ "type": "theme", "id": "uuid" }` or `{ "type": "feedback", "id": "uuid" }` or `{ "type": "customer", "id": "uuid" }`.

When page_context is provided, add it to the RAG context with higher priority.

### Sidebar Updates

- Add the chat floating button to the app layout (visible on all pages).
- The button shows a subtle animation or badge if there's a new conversation or suggested action.

### No Other Page Changes

The chat sidebar overlays on top of existing pages. No existing pages need modification beyond adding the floating chat button to the global layout.

---

## Prompt Templates

### backend/app/prompts/chat.py

Store the system prompt and tool definitions as template strings. Easy to find, easy to edit.

**System prompt template** with placeholders for:
- Product name and description
- Total feedback count
- Total theme count
- Current date

**Tool definition template** with all 7 tools described in the format the LLM expects.

### backend/app/prompts/title_generation.py

Short prompt for auto-generating conversation titles:
"Given this user message, generate a concise 3-6 word title for this conversation. Respond with only the title, no quotes or punctuation."

---

## Testing

### test_chat_service.py
1. Send message creates a new conversation if no conversation_id provided.
2. Send message appends to existing conversation.
3. Conversation history is loaded correctly (most recent N messages).
4. RAG context retrieves relevant feedback via embedding similarity.
5. RAG context includes theme summaries.
6. Context window management truncates when over budget.
7. Auto-title generates a short title from first message.
8. Conversation filters by user_id AND org_id (multi-tenant + per-user).

### test_tool_service.py
1. search_feedback_tool returns relevant items with filters.
2. get_theme_tool finds theme by name (fuzzy match).
3. get_theme_tool finds theme by ID (exact).
4. list_themes_tool returns ranked themes.
5. compare_segments_tool returns per-segment stats.
6. get_customer_feedback_tool returns customer's feedback.
7. get_stats_tool returns correct aggregate stats.
8. filter_feedback_tool applies multiple filters correctly.
9. execute_tool routes to correct function.
10. Unknown tool name returns error (not crash).

### test_rag_service.py
1. Retrieve relevant feedback returns items ordered by similarity.
2. Retrieve with filters (segment, urgency) narrows results.
3. Format feedback context produces concise string with key fields.
4. Format theme context includes names, scores, mention counts.
5. Token estimation is approximately correct.
6. Truncate context reduces items to fit budget.

### test_chat_routes.py
1. POST /chat/send with new conversation returns response and conversation_id.
2. POST /chat/send with existing conversation_id appends correctly.
3. GET /chat/conversations returns user's conversations only.
4. GET /chat/conversations from another user returns different list.
5. GET /chat/conversations/{id}/messages returns ordered messages.
6. DELETE /chat/conversations/{id} soft deletes.
7. Conversation from another org returns 404.
8. Conversation from another user in same org returns 404.

---

## Non-Negotiable Rules for This Phase

Everything from Phases 1-5 still applies, plus:

1. **Responses are grounded in data.** The LLM must never fabricate feedback quotes or customer names. Every claim in the response should trace back to actual data in the RAG context.
2. **Conversation history is per-user.** User A cannot see User B's conversations, even within the same org.
3. **Context window is managed.** Never send more context than the model can handle. Estimate tokens and truncate proactively.
4. **Tool calls have a maximum.** 3 tool calls per turn max. Prevents infinite loops.
5. **Chat never blocks other operations.** If the LLM is slow, it only affects the waiting PM. No Celery queue contention.
6. **Prompt templates in their own files.** System prompt and tool definitions in `backend/app/prompts/`, not inline.
7. **Raw context is stored.** Every assistant message stores context_used metadata. This is critical for debugging bad answers.
8. **Chat uses a separate model config.** Don't use the extraction model config for chat. Chat needs a smarter model with higher temperature.
9. **Page context is optional.** Chat works fine without it. Page context is an enhancement, not a requirement.

---

## What NOT to Build

- Evidence briefs (Phase 7)
- Solution design (Phase 7)
- Spec generation (Phase 8)
- Streaming responses (future enhancement — nice to have but not required for v1)
- Voice input (future)
- Chat sharing between users (future)
- Chat export (future)

---

## Acceptance Criteria

Phase 6 is complete when ALL of these are true:

- [ ] Chat sidebar opens and closes from a floating button on every page
- [ ] PM can type a question and get a response grounded in their data
- [ ] Response cites actual feedback quotes from the PM's data (not hallucinated)
- [ ] Response references theme names and priority scores when relevant
- [ ] Follow-up questions work (conversation context maintained)
- [ ] Suggested questions appear for new conversations
- [ ] Clicking a suggested question sends it as the first message
- [ ] PM can create new conversations
- [ ] PM can switch between conversations
- [ ] PM can delete conversations
- [ ] Conversations are per-user (user A can't see user B's chats)
- [ ] Conversations are per-org (org A can't see org B's data in chat)
- [ ] Tool functions work: search_feedback, get_theme, list_themes, compare_segments, get_customer_feedback, get_stats, filter_feedback
- [ ] RAG retrieves relevant feedback via pgvector similarity search
- [ ] Context window is managed (no token overflow errors)
- [ ] Page context works (asking about "this theme" on theme detail page works)
- [ ] Auto-generated conversation titles are meaningful
- [ ] Assistant messages render markdown properly
- [ ] Typing indicator shows while waiting for response
- [ ] Sources/context indicator shows what data was used
- [ ] Response time is under 10 seconds (acceptable for dev with local Llama)
- [ ] All Phase 6 tests pass
- [ ] All Phase 1-5 tests still pass

---

## How to Give This to Cursor

1. Save this file as `D:\LinkedIn\Week4\docs\PHASE_6_SPEC.md`
2. Open Cursor's chat and type:

> Read `docs/PHASE_6_SPEC.md`. This is the spec for Phase 6. The `.cursorrules` file still applies. Do NOT start building yet. Create a detailed implementation plan first: list every file you will create or modify, what each contains, the order of work, and dependencies. Present the full plan and wait for my approval.

3. Review the plan. Approve or push back.
4. Let Cursor build.
5. Run through acceptance criteria.

---

## After Phase 6

Once all acceptance criteria pass, come back for Phase 7: Evidence Briefs & Solution Design. That phase will add:
- One-click evidence brief generation for any theme (executive-ready document with problem statement, evidence, impact analysis, customer quotes, recommended action)
- Solution design assistant (PM describes a solution idea, system evaluates it against the evidence)
- Brief history and versioning
- Export to markdown/PDF
