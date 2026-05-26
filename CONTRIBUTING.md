# Contributing to Graphyte OSINT

Thanks for contributing. This project welcomes improvements across backend modules, frontend UX, documentation, and developer tooling.

## Local development

1. Fork and clone the repository.
2. Copy environment: `cp .env.example .env`
3. Start the stack: `npm run dev`
4. Open http://localhost:3000/dashboard
5. Run checks before opening a PR:
   - `make lint`
   - `make test`
   - `python test_all.py` (subprocess module validation)

## Branching and pull requests

- Create a feature branch from `main`.
- Keep PRs focused and scoped to one concern.
- Include clear reproduction and validation steps.
- Link related issues in the PR description.
- Include screenshots or terminal output for UI/runtime changes when relevant.

## Adding or updating an OSINT module

Follow this **6-touch** sequence (all required for a complete integration):

| Step | File | Action |
|------|------|--------|
| 1 | `backend/modules/<name>.py` | Implement `def run(...)` returning `{ "success": bool, ... }` |
| 2 | `backend/run_module.py` | Add `elif module_name == "<name>":` branch |
| 3 | `backend/tasks.py` | Add `@celery_app.task` + `_run_module_subprocess` call |
| 4 | `backend/normalize.py` | Title override, stats keys, table hooks if needed |
| 5 | `backend/stix_pipeline.py` | STIX mapping (or document why none applies) |
| 6 | `backend/api.py` | Pydantic request model + `POST /api/...` route |
| 7 | `backend/playbook.py` | Add to `ROUTING_MAP` + `MODULE_NAMES` for relevant types |
| 8 | `frontend/src/lib/api.ts` | Add `ModuleEndpoint` union member |
| 9 | `frontend/src/components/ModuleCards.tsx` | Add card definition |
| 10 | `backend/scripts/module_smoke.py` | Add smoke `Case` (optional but recommended) |

### Module implementation rules

1. **No stdout pollution** — never `print()` to stdout; use stderr or return data in the result dict. `run_module.py` redirects stdout during execution, but modules should not rely on this.
2. **Predictable JSON** — return a dict serializable with `json.dumps`; include `"success": true|false`.
3. **Keyless first** — modules should work without API keys; use env/config for optional upgrades.
4. **Graceful degradation** — missing optional deps → `{ "success": false, "error": "..." }`, not an unhandled exception.
5. **SSRF-safe targets** — only fetch user-supplied public targets; the API layer blocks private IPs and localhost.

### Subprocess test (without Celery)

```bash
echo '{"domain":"example.com"}' | python -m backend.run_module dns_intel
```

### Full module suite

```bash
python test_all.py
```

### API smoke (requires running stack)

```bash
python backend/scripts/module_smoke.py
```

## Frontend guidelines

- TypeScript **strict** — do not use `any`
- Use **Radix UI** + **Tailwind CSS** for new interactive components
- Beginner flows live on `/dashboard`; graph/terminal on `/workspace`
- Result display must consume the normalized envelope (`ok`, `summary`, `tables`, `errors`)

## Documentation

When adding modules or changing behavior, update:

- `README.md` (module table if user-facing)
- `API_DOCS.md` (new endpoint + body fields)
- `ARCHITECTURE.md` (if data flow changes)
- `knowledge.md` (agent reference)

## Commit conventions

- Use descriptive commit messages.
- Prefer one concern per commit.
- Never commit secrets, `.env` files, or generated local artifacts.

## Reporting bugs

Please use the issue templates:

- Bug report
- Feature request
- Module submission

## Community expectations

Be respectful and constructive. This project welcomes security researchers, developers, and analysts of all levels.
