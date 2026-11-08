# Agent Notes

- Use `uv` for Python commands and dependency management (`uv run`, `uv add`, `uv lock`).
- Main CLI: `training_data.py`; implemented with Typer. Check `--help` before changing commands.
- Store downloaded data under `parlament_data/`. Use Polars and Parquet (`.parquet`), not pickle.
- Keep datasets and Python transient files out of Git; update `.gitignore` if adding generated formats.
- Verify code changes with focused commands, such as `uv run python training_data.py samples --help` and a small sample read. Avoid unnecessary network downloads.
- User-facing usage examples belong in `README.md`; keep this file concise and current.
