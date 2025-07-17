"""CLI interface for the universal document processor."""

import os
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from .models import BatchProcessingRequest, ProcessingRequest
from .processor import UniversalDocumentProcessor
from .profiles.academic_paper import create_academic_paper_profile
from .profiles.language_textbook import create_language_textbook_profile

app = typer.Typer(help="Universal Document Processor - Convert PDFs to clean Markdown")
console = Console()


def get_api_key() -> str:
    """Get API key from environment or prompt user."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        api_key = typer.prompt("Enter your Google API key", hide_input=True)
    return api_key


@app.command()
def process(
    input_file: Path = typer.Argument(..., help="PDF file to process"),
    output_file: Path | None = typer.Option(
        None, "--output", "-o", help="Output markdown file"
    ),
    profile: str = typer.Option(
        "academic_paper", "--profile", "-p", help="Processing profile"
    ),
    start_page: int | None = typer.Option(
        None, "--start", "-s", help="Start page number"
    ),
    end_page: int | None = typer.Option(None, "--end", "-e", help="End page number"),
    force: bool = typer.Option(False, "--force", "-f", help="Force reprocessing"),
) -> None:
    """Process a single PDF document."""

    if not input_file.exists():
        console.print(f"❌ Input file not found: {input_file}", style="red")
        raise typer.Exit(1)

    # Get processing profile
    processing_profile = get_profile(profile)
    if not processing_profile:
        console.print(f"❌ Unknown profile: {profile}", style="red")
        raise typer.Exit(1)

    # Initialize processor
    api_key = get_api_key()
    processor = UniversalDocumentProcessor(api_key)

    # Create processing request
    request = ProcessingRequest(
        input_path=input_file,
        output_path=output_file,
        profile=processing_profile,
        start_page=start_page,
        end_page=end_page,
        force_reprocess=force,
    )

    # Process document
    result = processor.process_document(request)

    if result.success:
        console.print("\\n✅ Processing completed successfully!", style="green")
        console.print(f"📄 Output: {result.output_path}")
        console.print(f"📊 Quality Score: {result.metrics.calculate_score():.1f}")
    else:
        console.print("\\n❌ Processing failed!", style="red")
        for error in result.errors:
            console.print(f"   • {error}", style="red")
        raise typer.Exit(1)


@app.command()
def batch(
    input_dir: Path = typer.Argument(..., help="Directory containing PDF files"),
    output_dir: Path = typer.Argument(..., help="Output directory for processed files"),
    profile: str = typer.Option(
        "academic_paper", "--profile", "-p", help="Processing profile"
    ),
    pattern: str = typer.Option("*.pdf", "--pattern", help="File pattern to match"),
    recursive: bool = typer.Option(
        True, "--recursive/--no-recursive", help="Search recursively"
    ),
) -> None:
    """Process multiple PDF documents in batch."""

    if not input_dir.exists():
        console.print(f"❌ Input directory not found: {input_dir}", style="red")
        raise typer.Exit(1)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get processing profile
    processing_profile = get_profile(profile)
    if not processing_profile:
        console.print(f"❌ Unknown profile: {profile}", style="red")
        raise typer.Exit(1)

    # Initialize processor
    api_key = get_api_key()
    processor = UniversalDocumentProcessor(api_key)

    # Create batch request
    request = BatchProcessingRequest(
        input_directory=input_dir,
        output_directory=output_dir,
        profile=processing_profile,
        file_patterns=[pattern],
        recursive=recursive,
    )

    # Process batch
    results = processor.process_batch(request)

    # Summary
    successful = sum(1 for r in results if r.success)
    console.print(
        f"\\n🎯 Batch processing complete: {successful}/{len(results)} successful"
    )


@app.command()
def profiles() -> None:
    """List available processing profiles."""

    table = Table(title="Available Processing Profiles")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Description", style="white")

    # Add available profiles
    academic = create_academic_paper_profile()
    table.add_row("academic_paper", academic.document_type, academic.description)

    textbook = create_language_textbook_profile()
    table.add_row("language_textbook", textbook.document_type, textbook.description)

    console.print(table)


@app.command()
def benchmark(
    test_dir: Path = typer.Argument(..., help="Directory with test files"),
    profile: str = typer.Option(
        "academic_paper", "--profile", "-p", help="Profile to test"
    ),
) -> None:
    """Run benchmark tests on a set of documents."""

    if not test_dir.exists():
        console.print(f"❌ Test directory not found: {test_dir}", style="red")
        raise typer.Exit(1)

    # Get processing profile
    processing_profile = get_profile(profile)
    if not processing_profile:
        console.print(f"❌ Unknown profile: {profile}", style="red")
        raise typer.Exit(1)

    # Find test files
    test_files = list(test_dir.glob("*.pdf"))
    if not test_files:
        console.print(f"❌ No PDF files found in {test_dir}", style="red")
        raise typer.Exit(1)

    console.print(f"🧪 Running benchmark on {len(test_files)} files...")

    # Initialize processor
    api_key = get_api_key()
    processor = UniversalDocumentProcessor(api_key)

    # Process each test file
    results = []
    for test_file in test_files:
        console.print(f"\\n📄 Testing: {test_file.name}")

        request = ProcessingRequest(input_path=test_file, profile=processing_profile)

        result = processor.process_document(request)
        results.append(result)

    # Display benchmark results
    display_benchmark_results(results, processing_profile)


def display_benchmark_results(results: list[Any], profile: Any) -> None:
    """Display benchmark test results."""

    table = Table(title=f"Benchmark Results - {profile.name}")
    table.add_column("File", style="cyan")
    table.add_column("Success", style="green")
    table.add_column("Quality", style="magenta")
    table.add_column("Time (s)", style="yellow")
    table.add_column("Pages", style="blue")

    total_time = 0
    successful = 0
    total_quality = 0

    for result in results:
        quality_score = result.metrics.calculate_score()
        total_time += result.processing_time
        total_quality += quality_score

        if result.success:
            successful += 1
            success_icon = "✅"
        else:
            success_icon = "❌"

        table.add_row(
            result.input_path.name,
            success_icon,
            f"{quality_score:.1f}",
            f"{result.processing_time:.1f}",
            str(result.metrics.pages_processed),
        )

    console.print(table)

    # Summary stats
    avg_quality = total_quality / len(results)
    success_rate = successful / len(results) * 100

    console.print("\\n📊 Summary:")
    console.print(f"   Success Rate: {success_rate:.1f}%")
    console.print(f"   Average Quality: {avg_quality:.1f}")
    console.print(f"   Total Time: {total_time:.1f}s")
    console.print(f"   Average Time: {total_time / len(results):.1f}s/file")

    # Check if meets minimum standards
    if avg_quality >= profile.min_quality_score:
        console.print(
            f"✅ Benchmark PASSED (avg quality {avg_quality:.1f} >= {profile.min_quality_score})",
            style="green",
        )
    else:
        console.print(
            f"❌ Benchmark FAILED (avg quality {avg_quality:.1f} < {profile.min_quality_score})",
            style="red",
        )


def get_profile(profile_name: str) -> Any:
    """Get processing profile by name."""
    profiles = {
        "academic_paper": create_academic_paper_profile(),
        "language_textbook": create_language_textbook_profile(),
    }

    return profiles.get(profile_name)


if __name__ == "__main__":
    app()
