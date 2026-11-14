## Chat-like Responses — Suggestions and Plan (without LangChain first)

> Status: **Proposed** · Context: `POST /api/v1/query` on the `product_ast` (RF) collection
> Related: [LangChain_Integration_Plan.md](LangChain_plan/LangChain_Integration_Plan.md),
> [RF_collection_plan.md](../work_private/RF_collection_plan.md) (§9.7)

---

### 1. Problem

A query such as "What are the keywords to restart Net" (`collection_name=product_ast`,
`project=net`, `type=keyword`) returns a correct-ish but raw response:

- Plain-text answer, no fixed structure.
- Large `sources` objects (full chunk text, duplicated `heading` / `metadata.heading`).
- Latency of ~18 s with no feedback until the whole answer is ready.
- No conversation context (each request is stateless).
- The endpoint accepts form data only.

**Decision:** a "nicer, chat-like" output is mainly a **prompt + presentation** problem.
LangChain is **not required** as the base for it.

---

### 2. Observations from the sample response

1. **Answer quality**
   - `Stop Net`, `Start Net services`, `Restart services and relogin` are relevant.
   - `Net_TopMenu.click application logo` is **not** a restart keyword; it was listed because it
     appeared in the `Clean database` chunk. The prompt does not force the LLM to list only keywords
     that perform the action.
2. **Source ordering**
   - First hits have `distance: null` and `"match": "lexical"` → lexical hits are placed
     before vector hits, so the order is not by relevance.
   - Vector distances ~275–286 look like L2 distance on unnormalized vectors, not cosine.
     Check the collection's distance metric (`hnsw:space`) separately.
3. **Request format**
   - Form-encoded input is awkward for chat clients; a JSON body is preferable.

---

### 3. Plan (ordered by effort)

#### Step 1 — Better prompt (~1 h, no new dependency)
- Add optional `system_prompt` / `prompt_template` parameter to `query_and_generate`
  (default = current behaviour, so `product_docs` is unaffected; see RF plan §9.7).
- RF prompt rules:
  - List keyword names **exactly** as in the context.
  - One-line purpose + source file per keyword.
  - Do not include keywords that do not perform the requested action.
  - If nothing matches, say so.
- Ask for Markdown with a fixed structure:
  1. Short answer
  2. Bullet list: `` `Keyword` (`file`) – purpose ``
  3. Related (optional)

#### Step 2 — Clean response model (~1 h)
- Return structured sources (`RobotKeywordResult`): `name`, `type`, `source_file`, `args` (list),
  `score`, `snippet` (trimmed text).
- Remove duplicated `heading` / `metadata.heading`; keep full text only behind an option
  (e.g. `include_text=true`).
- Fix ordering: sort merged lexical + vector hits consistently (e.g. reciprocal rank fusion) and
  always provide a score.
- Accept a JSON body in addition to form data.

#### Step 3 — Streaming (~0.5 day)
- `ollama.generate(stream=True)` + FastAPI `StreamingResponse` (SSE or chunked text).
- Send sources first (or last), then tokens. Biggest improvement in perceived speed.

#### Step 4 — Simple chat memory (~0.5 day)
- Optional `session_id`; in-memory history of the last N turns (same pattern as the job store,
  with TTL cleanup).
- Rewrite follow-up questions into standalone queries with one extra LLM call before retrieval.
  Equivalent to LangChain's history-aware retriever in ~30 lines.

#### Step 5 — Chat UI (optional)
- Small Streamlit or Gradio page calling the API (streaming + sources panel). No LangChain needed.

---

### 3a. Implementation status (Steps 1 & 2) — tested 2026-11-14

**Implemented**
- `src/rag/vectorstore.py`: `system_prompt` parameter on `query_and_generate`; `RF_SYSTEM_PROMPT` is used
  automatically when retrieved chunks are keyword/testcase/locator/python_keyword (docs prompt unchanged).
- `src/api/models.py`: `SourceInfo` (name, type, project, source_file, args[], tags[], score, match, snippet,
  optional text), `QueryRequest`, `QueryResponse.sources: List[SourceInfo]`.
- `src/api/routes/query.py`: shared `_run_query`, compact sources, `include_text` option,
  new `POST /api/v1/query/json` (JSON body). Form endpoint `POST /api/v1/query` kept.

**Tested** (`product_ast`, `project=net`, `type=keyword`, "keywords to restart Net")

| Check | Result |
|---|---|
| `POST /query/json` | ✅ works, ~12 s |
| `POST /query` (form) | ✅ works, ~10 s |
| Compact sources (no duplicated heading/metadata, args as list, 300-char snippet) | ✅ |
| `click application logo` no longer listed as a restart keyword | ✅ |
| Answer lists real restart keywords (`Stop Net`, `Start Net services`) | ✅ |

**Remaining problems found**
1. **Prompt compliance is only partial** (llama3.1:8b): output format varies between runs (once with
   Answer/Related sections, once just two bold lines); literal "(file)" placeholder printed in one run;
   argument text (`timeout=5 min`) merged into the keyword name; in one run the file was attributed wrongly
   (`Stop Net` → `Net_Common` instead of `NetShare`); "Related" sometimes includes loosely related items.
   → Options: stronger/shorter prompt with a concrete example, `temperature=0` via `options`, bigger model.
2. **Source ordering unchanged**: lexical hits (`score: null`) are still first and are weakly relevant
   (`Log in after Net restart`, wildfly config keyword), while the keywords that actually answer
   (`Stop Net`, `Start Net services`) are not in `sources` at all — they only appear inside other chunks' bodies.
   → Needs ranking work (e.g. rank fusion) and/or better lexical scoring (name match on `restart` + `Net` ranks
   `Stop`/`Start Net services` lower than keywords containing "restart" in the name).
3. **Distances ~275–312** still look like L2 on unnormalized vectors; `hnsw:space` not yet checked.

**Next:** fix 1 (prompt example + `temperature=0`), then 2 (merge ranking), then 3 (distance metric); Steps 3–5 as planned.

---

### 4. When LangChain becomes worth it

- Agent routing (LLM chooses between keyword search, test search, web search tools).
- Multi-query retrieval or re-ranking across several collections.
- Preference for maintained memory/streaming building blocks over custom code.

**Risks that still apply** (see LangChain plan §6): metadata `where` filters, scores dropped by
`create_retrieval_chain`, MMR being the wrong default for exact keyword lookup. The existing hybrid
lexical + vector search with `where` filters is custom behaviour LangChain would make harder.

---

### 5. Recommendation

1. Do **Steps 1 and 2** now.
2. Add **Step 3** if latency is annoying, **Step 4** if real multi-turn chat is wanted.
3. Revisit LangChain only for agent-style needs.

### 6. Acceptance criteria

- Answers list only keywords that perform the requested action, in a consistent Markdown format.
- `sources` are compact, ordered by relevance, always with a score.
- `product_docs` queries behave as before (defaults unchanged).
- (Optional) tokens stream to the client; follow-up questions work via `session_id`.

### 7. Files likely affected

| File | Change |
|---|---|
| `src/rag/vectorstore.py` | `system_prompt` parameter; hybrid result ordering/scores |
| `src/api/routes/query.py` | JSON body support, structured sources, streaming, `session_id` |
| `src/api/models.py` | `RobotKeywordResult`, updated query request/response models |
| `src/api/dependencies.py` | in-memory chat session store (Step 4) |

