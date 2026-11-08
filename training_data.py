# %%
from datetime import datetime, timezone
from pathlib import Path

import polars as pl
import typer
from tqdm import tqdm
from swissparlpy import SwissParlClient

FOLDER = Path("parlament_data")
START_YEAR = 2000
END_YEAR = 2001  # Exclusive


def save_businesses(
    client: SwissParlClient,
    folder: Path,
    language: str = "DE",
) -> Path:
    """Download business records, including their descriptions, as Parquet."""
    folder.mkdir(parents=True, exist_ok=True)
    filename = folder / f"businesses_{language.lower()}.parquet"
    businesses = client.get_data("Business", Language=language)
    typer.echo(f"Downloading {language} business records...")
    df = pl.DataFrame(list(businesses))
    df.write_parquet(filename)
    typer.echo(f"Saved {df.height} business records to {filename}")
    return filename


def save_transcripts(
    client: SwissParlClient,
    folder: Path,
    year: int,
) -> Path:
    """Download one year's German transcripts and save them as Parquet."""
    date_from = datetime(year, 1, 1, tzinfo=timezone.utc)
    date_to = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    filename = folder / f"transcripts_{year}.parquet"

    transcripts_data = client.get_data(
        "Transcript",
        Language="DE",
        Start__gte=date_from,
        Start__lt=date_to,
    )

    rows = list(tqdm(transcripts_data, desc=f"Transcripts {year}", unit="row"))
    df = pl.DataFrame(rows)
    print(f"{df.height} rows loaded for {year}")
    df.write_parquet(filename)
    print(f"Data saved to {filename}")
    return filename


def load_transcripts(folder: Path = FOLDER) -> pl.DataFrame:
    """Load the combined Parquet file, or combine yearly Parquet files."""
    combined_file = folder / "all_transcripts.parquet"
    if combined_file.exists():
        return pl.read_parquet(combined_file)

    files = sorted(folder.glob("transcripts_*.parquet"))
    if not files:
        raise FileNotFoundError(f"No transcript Parquet files found in {folder}")

    frames = [pl.read_parquet(file_path) for file_path in files]
    return pl.concat(frames, how="diagonal_relaxed")


def read_transcript_samples(
    n: int = 5,
    folder: Path = FOLDER,
    file_path: Path | None = None,
) -> pl.DataFrame:
    """Read the first n samples from a Parquet file or the saved transcript collection."""
    if n < 0:
        raise ValueError("n must be non-negative")
    if file_path is not None:
        if not file_path.is_file():
            raise FileNotFoundError(f"Parquet file not found: {file_path}")
        return pl.read_parquet(file_path).head(n)
    return load_transcripts(folder).head(n)


def load_businesses(folder: Path = FOLDER, language: str = "DE") -> pl.DataFrame:
    """Load downloaded business records containing titles and descriptions."""
    filename = folder / f"businesses_{language.lower()}.parquet"
    if not filename.exists():
        raise FileNotFoundError(
            f"Business data not found at {filename}; run the businesses download command first."
        )
    return pl.read_parquet(filename)


app = typer.Typer(help="Download and inspect Swiss parliamentary transcripts and business descriptions.")


@app.command()
def download(
    start_year: int = typer.Option(START_YEAR, help="First year to download."),
    end_year: int = typer.Option(END_YEAR, help="Last year to download (exclusive)."),
    folder: Path = typer.Option(FOLDER, help="Directory for transcript Parquet files."),
) -> None:
    """Download yearly transcripts and combine them into one Parquet file."""
    if end_year <= start_year:
        raise typer.BadParameter("end-year must be greater than start-year")

    folder.mkdir(parents=True, exist_ok=True)
    client = SwissParlClient(backend="odata")

    for year in tqdm(range(start_year, end_year), desc="Years", unit="year"):
        filepath = folder / f"transcripts_{year}.parquet"
        if filepath.exists():
            tqdm.write(f"Skipping {year}, already downloaded.")
            continue

        tqdm.write(f"Downloading transcripts for year {year}")
        save_transcripts(client, folder, year)

    transcripts = load_transcripts(folder)
    typer.echo(f"\nTotal transcripts: {transcripts.height}")
    combined_file = folder / "all_transcripts.parquet"
    transcripts.write_parquet(combined_file)
    typer.echo(f"Combined data saved to {combined_file}")


@app.command()
def businesses(
    language: str = typer.Option("DE", help="Business language, e.g. DE, FR, IT."),
    folder: Path = typer.Option(FOLDER, help="Directory for downloaded business data."),
    business_number: str | None = typer.Option(
        None, help="Optional business number, e.g. 99.3378, to download one record."
    ),
) -> None:
    """Download business records, including descriptions and motion text."""
    folder.mkdir(parents=True, exist_ok=True)
    client = SwissParlClient(backend="odata")

    if business_number:
        filename = folder / f"business_{business_number.replace('.', '-')}_{language.lower()}.parquet"
        rows = client.get_data(
            "Business",
            filter=f"BusinessShortNumber eq '{business_number}' and Language eq '{language.upper()}'",
        )
        df = pl.DataFrame(list(rows))
        if df.is_empty():
            raise typer.BadParameter(f"No business found for number {business_number} ({language.upper()})")
        df.write_parquet(filename)
        typer.echo(f"Saved business {business_number} to {filename}")
    else:
        save_businesses(client, folder, language.upper())


@app.command()
def samples(
    n: int = typer.Option(5, min=0, help="Number of samples to display."),
    folder: Path = typer.Option(FOLDER, help="Directory containing transcript Parquet files."),
    file_path: Path | None = typer.Option(
        None, "--file", "-f", help="Path to a Parquet file to read samples from."
    ),
    show_text: bool = typer.Option(True, "--show-text/--no-show-text", help="Include full transcript text."),
) -> None:
    """Read and print sample rows, including transcript text by default."""
    try:
        data = read_transcript_samples(n=n, folder=folder, file_path=file_path)
    except FileNotFoundError as exc:
        raise typer.BadParameter(str(exc)) from exc

    if show_text and "Text" in data.columns:
        for index, row in enumerate(data.iter_rows(named=True), start=1):
            typer.echo(f"\n--- Transcript sample {index} ---")
            typer.echo(f"ID: {row.get('ID')}")
            typer.echo(f"Speaker: {row.get('SpeakerFullName')}")
            typer.echo(
                f"Parliamentary group: {row.get('ParlGroupName') or '[not available]'}"
                f" ({row.get('ParlGroupAbbreviation') or 'no abbreviation'})"
            )
            typer.echo(f"Date: {row.get('MeetingDate')}")
            typer.echo(f"Language: {row.get('Language')}")
            typer.echo("\nTranscript text:\n")
            typer.echo(row.get("Text") or "[No transcript text available]")
    else:
        typer.echo(data)


if __name__ == "__main__":
    app()
