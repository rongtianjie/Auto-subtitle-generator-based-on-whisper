# Root Layout Cleanup Design

## Goal

Make the repository root easier to scan by moving long-form documentation into `docs/` and moving Docker build assets into `docker/`, while keeping the day-to-day developer commands unchanged.

## Scope

- Move current top-level docs into `docs/`
- Move the active Docker build files into `docker/`
- Keep `docker-compose.yml` in the repository root
- Update all references to moved files in Compose config, Makefile, and active documentation
- Preserve the current user-facing workflow:
  - `docker compose up -d`
  - `docker compose build --no-cache`
  - `make docker-up`

## Structure

### Root keeps only key entry points

- `README.md`
- `Makefile`
- `docker-compose.yml`
- `backend/`
- `frontend/`
- `docs/`
- `docker/`
- existing infra/application directories that are already grouped (`k8s/`, `monitoring/`, `archive/`, etc.)

### Documentation moves

- `API_DOCUMENTATION.md` -> `docs/API_DOCUMENTATION.md`
- `CONTRIBUTING.md` -> `docs/CONTRIBUTING.md`
- `DEPLOYMENT_GUIDE.md` -> `docs/DEPLOYMENT_GUIDE.md`
- `DEVELOPMENT.md` -> `docs/DEVELOPMENT.md`
- `LOGGING_GUIDE.md` -> `docs/LOGGING_GUIDE.md`
- `MONITORING_GUIDE.md` -> `docs/MONITORING_GUIDE.md`

### Docker assets move

- `Dockerfile.backend` -> `docker/Dockerfile.backend`
- `Dockerfile.frontend` -> `docker/Dockerfile.frontend`
- `backend/docker-entrypoint.sh` -> `docker/backend-entrypoint.sh`

## Command Compatibility

The main command surface should not change.

- `docker-compose.yml` will reference `docker/Dockerfile.backend` and `docker/Dockerfile.frontend`
- backend image build steps will copy `docker/backend-entrypoint.sh`
- `Makefile` Docker targets will use the new file paths
- docs examples will still tell users to run commands from the repo root

## Validation

- `docker compose config` succeeds
- `make` targets referencing Docker paths still resolve
- no broken local links remain in active docs

## Risks

- Broken file references in docs or scripts after moving files
- Compose build failures if Dockerfile/script paths are missed
- Broken markdown links if docs are moved without updating references

## Recommendation

Use the middle-ground cleanup: cleaner root layout without changing how contributors build or run the project.
