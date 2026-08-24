# FlyRank Backend Assignment 6 — AI-generated submission

The submission lives in:

`artifacts/flyrank-backend-assignment-6/`

Start here:

- [`artifacts/flyrank-backend-assignment-6/README.md`](artifacts/flyrank-backend-assignment-6/README.md)
- [`artifacts/flyrank-backend-assignment-6/JOB-CARD.md`](artifacts/flyrank-backend-assignment-6/JOB-CARD.md)
- [`artifacts/flyrank-backend-assignment-6/docs/verification.md`](artifacts/flyrank-backend-assignment-6/docs/verification.md)

The surrounding repository is the original Replit workspace used to build and verify the assignment. It is retained for provenance; reviewers do not need to inspect unrelated workspace packages.

## Fast verification

```bash
python -m pip install "fastapi>=0.115" "httpx>=0.28" "pydantic>=2.10" "pytest>=8" "uvicorn>=0.30"
PYTHONPATH=artifacts/flyrank-backend-assignment-6 \
python -m pytest artifacts/flyrank-backend-assignment-6/backend/tests -q
```

The GitHub Actions workflow `.github/workflows/assignment-6-s3.yml` runs the contract tests, labelled evaluation, and deterministic HTTP checkpoint.
