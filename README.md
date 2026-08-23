# Sentiment Judge

LLM-scored sentiment analysis (-100..100) with validator consensus.

Built with [GenLayer](https://genlayer.com) intelligent contracts: deterministic
on-chain state plus nondeterministic LLM/web calls settled by validator
consensus (`gl.vm.run_nondet_unsafe`).

## Contract

- Main entry point: `analyze_text()`
- Pinned runner: `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` (genvm v0.3.0-rc7)
- Storage: `TreeMap`/`DynArray`/`u256`; payouts via `emit_transfer(on="finalized")`
- All LLM/web access happens inside leader/validator closures; expected user
  errors use the `[EXPECTED]` prefix.

## Tests

Direct-mode tests mock all LLM/web nondeterminism (no network needed):

```
python -m pytest tests/direct -v
```

Requires the packages in `requirements.txt`.

## Layout

```
contracts/   intelligent contract source
tests/       direct-mode pytest suite
```

## Deployment

Deployed on GenLayer studionet as `SentimentJudge` at `0x743C2E90f53C7cFF539235813f19789E2e991e71`.
See the root `DEPLOYMENTS.md` in the workspace bundle for the full registry.
