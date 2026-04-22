# Contributing to OSINT Digital Footprint Visualizer

Thanks for contributing. This project welcomes improvements across backend modules, frontend UX, documentation, and developer tooling.

## Local development

1. Fork and clone the repository.
2. Start the stack: `npm run dev`
3. Run checks before opening a PR:
   - `make lint`
   - `make test`

## Branching and pull requests

- Create a feature branch from `main`.
- Keep PRs focused and scoped to one concern.
- Include clear reproduction and validation steps.
- Link related issues in the PR description.
- Include screenshots or terminal output for UI/runtime changes when relevant.

## Adding or updating a module

When adding a new OSINT module, follow this sequence:

1. Create `backend/modules/<module_name>.py`
2. Add a Celery task in `backend/tasks.py`
3. Normalize output in `backend/normalize.py`
4. Add STIX mapping in `backend/stix_pipeline.py` as needed
5. Expose API route in `backend/api.py`
6. Add frontend entry points in `frontend/src/app/tools` or playbook routing surfaces

All modules should return predictable outputs and support failure envelopes for frontend rendering.

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
