# Maturarbeit

Tools for downloading and inspecting Swiss parliamentary transcripts and parliamentary business records using `swissparlpy`, Polars, and Typer.

## Setup

Install [uv](https://docs.astral.sh/uv/) if it is not already available, then sync the project environment:

```fish
uv sync
```

## Transcript data

Download transcript records for a year range. The end year is exclusive:

```fish
uv run python training_data.py download --start-year 2001 --end-year 2002
```

This downloads German transcripts into `parlament_data/transcripts_<year>.parquet` and creates or refreshes `parlament_data/all_transcripts.parquet` from yearly Parquet files in that folder.

Show five transcript samples from the combined file:

```fish
uv run python training_data.py samples --n 5
```

Read samples from a specific Parquet file instead:

```fish
uv run python training_data.py samples --file parlament_data/transcripts_2001.parquet --n 5
```

Use `--no-show-text` to display the compact Polars table without printing full transcript text.

## Parliamentary business records

Download German business records, including descriptions and motion text:

```fish
uv run python training_data.py businesses --language DE
```

Download one business record by its short number:

```fish
uv run python training_data.py businesses --business-number 99.3378 --language DE
```

The individual record is saved as a Parquet file under `parlament_data/`. Read it with Polars, for example:

```fish
uv run python -c 'import polars as pl; df = pl.read_parquet("parlament_data/business_99-3378_de.parquet"); print(df.select("Title", "Description", "SubmittedText", "ReasonText"))'
```

## Notes

- `--start-year` is inclusive and `--end-year` is exclusive.
- Existing yearly transcript files are skipped during downloads.
- Parquet datasets and Python cache files are ignored by Git.
