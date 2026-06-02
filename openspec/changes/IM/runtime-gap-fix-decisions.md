# Runtime Gap Fix Decisions

## 2026-05-29

### Runtime Protocol: Direct Reply First, Action Only When Needed

**Decision**: The runtime adopts a dual-mode response protocol. Models may respond in either mode:

1. **Direct Reply Mode** (default for ordinary conversation): Plain natural language text is a valid and preferred final answer. No `<action>` wrapping required.
2. **Action Mode** (when tools are needed): Output `<action><tool_name>...</tool_name></action>` to invoke a tool. Use `<task_complete>` only when the overall task is genuinely finished.

**Rationale**: The previous mandatory two-block format (`<thinking>` + `<action>`) imposed unnecessary protocol overhead on simple responses and was incompatible with models that frequently produced malformed XML. Direct reply reduces format-following errors and improves streaming UX.

**Scope**: Backend runtime (react_agent.py), runtime_agent_service.py, system_prompt.j2.

### Backward Compatibility

**Decision**: Action-mode responses are unaffected. The `<action><task_complete>...</task_complete></action>` path remains fully functional. All existing tests pass without modification.

### Fallback Scope: Low-Signal Only

**Decision**: Non-streaming fallback (retry without streaming) is triggered only when the streaming aggregate is classified as "low-signal" (contains no visible characters). Normal streaming text — even if it includes markdown headers or partial content — does NOT trigger fallback.

**Low-signal examples**: `####`, `# 标题`, `<thinking></thinking>`, whitespace-only strings.
**NOT low-signal**: `#### 正常内容`, `你好，世界`, `### 标题\n正文`.

**Rationale**: Fallback was previously applied to all non-task_complete responses, causing unnecessary latency on normal streaming responses. Restricting it to low-signal content preserves speed for the majority of responses.

### Frontend Streaming UX: No Low-Signal Flash

**Decision**: During streaming, low-signal chunks (markdown headers with no content, pure protocol tags) that appear as leading content are suppressed from the visible display. Once meaningful content has been received, subsequent content is displayed as-is to preserve visual continuity.

**Rationale**: Users previously saw "####" briefly appear before normal text in streaming responses, creating a jarring flash effect.

### Protocol Classification Logging

**Decision**: Runtime adds explicit protocol classification logs to aid debugging:

- `response classified as direct_reply`: Model output contained no `<action>` tag
- `response classified as action_call`: Model output contained an `<action>` tag with a recognized tool

These supplement existing logs (provider model, streaming preview, fallback preview, final_content preview).

### Incomplete Identity Prefix Fallback

**Decision**: Short Chinese identity-prefix replies such as `我是` are treated as incomplete direct replies during streaming and trigger the existing non-streaming fallback path instead of being finalized immediately.

**Rationale**: In prompts like `你是谁`, some models emit only the opening identity prefix in the streaming aggregate. Without this guard, the runtime would persist and display a broken half-sentence as the final reply.

### Incomplete XML Prefix Fallback

**Decision**: Single-token XML or protocol prefixes such as `<`, `</`, `<a`, and `<t` are treated as incomplete direct replies during streaming and trigger the existing non-streaming fallback path.

**Rationale**: Some models begin structured output with a bare XML prefix before the rest of the payload arrives. Without this guard, the runtime may classify the prefix as a normal direct reply and persist a lone `<` as the final answer.

---

## Historical Decisions

- 2026-05-29: When the runtime receives a model response without `<action>`, it must not pass protocol XML through to the DB or frontend unchanged.
- 2026-05-29: Thinking-only protocol markup such as `<thinking>` and `execution_analysis` is normalized into visible plain text before `message_end.final_content` is emitted.
- 2026-05-29: The `task_complete` example in the runtime system prompt uses `<answer>` so the prompt matches the actual tool schema.
