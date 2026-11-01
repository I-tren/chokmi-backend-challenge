"""Part 3 — versioned prompt registry + governed invoker.

Mirrors Chokmi's `llm_runtime`: every LLM call goes through a registry with
intended-use gating, PII masking, a per-tenant cost ceiling, and structured
output validation. Implement `PromptRegistry` and `LLMRuntime`.

PromptVersion(id, version, template, intended_use, output_schema, max_output_tokens)
    template        str with `{name}` placeholders (use only simple names)
    intended_use    frozenset[str]
    output_schema   dict[str, type]   exact top-level keys and types
    max_output_tokens int

PromptRegistry
    register(pv)  versions start at 1 and must be contiguous. Re-registering an
                  identical (id, version) is a no-op; a different body for an
                  existing (id, version) raises `ImmutableVersionError`;
                  a gap (e.g. v3 when latest is v1) raises `ValueError`.
    get(id, version=None) -> PromptVersion   latest when version is None;
                  KeyError if unknown.

LLMRuntime(registry, provider, ceilings, price_per_1k_micros, max_attempts=3)
    provider(prompt: str, max_tokens: int) -> (text: str, tokens_used: int)
              may raise `ProviderError` (transient).
    ceilings  dict[tenant -> int micro-units]; unknown tenant -> ValueError
    invoke(tenant, prompt_id, variables, purpose, version=None) -> dict
    spent(tenant) -> int
    log -> list[dict]  one entry per attempt (and per blocked call):
              {"tenant","prompt_id","version","attempt","status","tokens","cost"}
              status in {"ok","invalid","provider_error","blocked_use",
                         "blocked_budget"}

Rules, in this order:
1. `purpose` not in the prompt's intended_use -> raise `IntendedUseError`
   BEFORE touching the provider; log a "blocked_use" entry.
2. `variables` must match the template placeholders exactly (missing or extra
   -> ValueError). String values are PII-masked BEFORE rendering: e-mail
   addresses -> "[EMAIL]", runs of 7+ digits (allowing spaces, dashes, dots,
   parentheses and a leading +) -> "[PHONE]". The provider must never see raw
   PII. Non-string values are rendered with str().
3. Before every attempt, worst-case cost =
   ceil((len(prompt)//4 + max_output_tokens) * price_per_1k_micros / 1000).
   If spent + worst-case > ceiling -> raise `BudgetExceeded`, no provider
   call, log "blocked_budget".
4. After a provider call, charge ceil(tokens_used * price / 1000) — also for
   outputs that turn out to be invalid. Provider exceptions cost nothing.
5. Output must be a JSON object whose keys equal output_schema's keys and whose
   values have exactly those types (bool is NOT an int; int is acceptable for
   a float field, but not vice-versa). Invalid -> retry with the original prompt
   plus "\\nPrevious output invalid: <reason>" up to max_attempts attempts in
   total (provider errors count as attempts). Budget is re-checked each
   attempt. Exhausted -> raise `OutputInvalid` (or ProviderError if the last
   failure was the provider).
6. Concurrency: invoke may be called from many threads; spend must never
   exceed the ceiling.
"""
import math  # noqa: F401


class ProviderError(Exception): ...
class IntendedUseError(Exception): ...
class BudgetExceeded(Exception): ...
class OutputInvalid(Exception): ...
class ImmutableVersionError(Exception): ...


class PromptVersion:
    def __init__(self, id, version, template, intended_use, output_schema, max_output_tokens):
        raise NotImplementedError


class PromptRegistry:
    def register(self, pv):
        raise NotImplementedError

    def get(self, prompt_id, version=None):
        raise NotImplementedError


class LLMRuntime:
    def __init__(self, registry, provider, ceilings, price_per_1k_micros, max_attempts=3):
        raise NotImplementedError

    def invoke(self, tenant, prompt_id, variables, purpose, version=None):
        raise NotImplementedError

    def spent(self, tenant):
        raise NotImplementedError

    @property
    def log(self):
        raise NotImplementedError
