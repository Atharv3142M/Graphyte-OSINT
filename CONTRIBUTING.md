# Contributing to OSINT Digital Footprint Visualizer

Thanks for contributing.

## Development setup

1. Fork and clone the repository.
2. Start infrastructure: `docker compose up -d`
3. Install backend deps: `pip install -r backend/requirements.txt`
4. Install frontend deps: `cd frontend && npm install`
5. Run locally: `python main.py`

## Branching and pull requests

- Create a feature branch from `main`.
- Keep PRs focused and small when possible.
- Include clear reproduction and validation steps.
- Link related issues in the PR description.

## Code quality checks

Run before opening a PR:

- `make lint`
- `make test`

If `make` is unavailable on your platform, run the equivalent commands from `Makefile`.

## Module contribution guide (backend + UI)

When adding a new OSINT module, follow this sequence:

1. Create `backend/modules/<module_name>.py`
2. Add a Celery task in `backend/tasks.py`
3. Add STIX mapping in `backend/stix_pipeline.py`
4. Expose API route in `backend/api.py`
5. Add a UI card/entry point in `frontend/src/app/tools`

Keep output schema consistent so module results are renderable and mappable into STIX entities.

## Commit conventions

- Use descriptive commit messages.
- Prefer one concern per commit.
- Avoid committing secrets, `.env` files, or generated local artifacts.

## Reporting bugs

Please use the issue templates:

- Bug report
- Feature request
- Module submission

## Community expectations

Be respectful and constructive. This project welcomes security researchers, developers, and analysts of all levels.
