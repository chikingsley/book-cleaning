"""Core universal document processor engine."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import google.generativeai as genai  # type: ignore[import-untyped]
from pdf2image import convert_from_path
from PIL import Image
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from .models import (
    BatchProcessingRequest,
    ProcessingRequest,
    ProcessingResult,
    QualityMetrics,
)
from .utils.post_processor import UniversalPostProcessor


class UniversalDocumentProcessor:
    """Universal document processor with configurable profiles."""

    def __init__(self, api_key: str | None = None):
        """Initialize the processor with API key."""
        self.console = Console()
        self.post_processor = UniversalPostProcessor()

        if api_key:
            genai.configure(api_key=api_key)

        # Initialize Gemini model
        self.model: genai.GenerativeModel | None = None
        self._current_model_name: str | None = None

    def _initialize_model(self, model_name: str) -> None:
        """Initialize the Gemini model if not already done."""
        if self.model is None or model_name != self._current_model_name:
            self.model = genai.GenerativeModel(model_name)
            self._current_model_name = model_name

    def process_document(self, request: ProcessingRequest) -> ProcessingResult:
        """Process a single document with the specified profile."""
        start_time = time.time()

        self.console.print(f"\\n🚀 Processing: {request.input_path.name}", style="bold blue")
        self.console.print(f"📋 Profile: {request.profile.name}")
        self.console.print(f"🤖 Model: {request.profile.model_name}")

        try:
            # Initialize model
            self._initialize_model(request.profile.model_name)

            # Convert PDF to images
            image_paths = self._convert_pdf_to_images(
                request.input_path,
                request.start_page,
                request.end_page,
                request.profile.image_scale
            )

            if not image_paths:
                return ProcessingResult(
                    success=False,
                    input_path=request.input_path,
                    metrics=QualityMetrics(),
                    errors=["Failed to convert PDF to images"]
                )

            # Process images with OCR
            batch_results = self._process_images_in_batches(
                image_paths,
                request.profile
            )

            # Combine and post-process results
            combined_text = self._combine_batch_results(batch_results)

            if not combined_text:
                return ProcessingResult(
                    success=False,
                    input_path=request.input_path,
                    metrics=QualityMetrics(),
                    errors=["No text extracted from document"]
                )

            # Apply post-processing
            final_text, metrics = self.post_processor.process_text(
                combined_text,
                request.profile
            )

            # Save results
            output_path = self._save_results(
                final_text,
                request.input_path,
                request.output_path,
                request.profile,
                metrics,
                batch_results
            )

            processing_time = time.time() - start_time
            metrics.processing_time_seconds = processing_time

            # Check quality
            quality_score = metrics.calculate_score()
            success = quality_score >= request.profile.min_quality_score

            if not success:
                self.console.print(
                    f"⚠️ Quality score {quality_score:.1f} below threshold {request.profile.min_quality_score}",
                    style="yellow"
                )

            result = ProcessingResult(
                success=success,
                input_path=request.input_path,
                output_path=output_path,
                metrics=metrics,
                processing_time=processing_time,
                batch_results=batch_results
            )

            self._display_results(result)
            return result

        except (OSError, ValueError, RuntimeError) as e:
            return ProcessingResult(
                success=False,
                input_path=request.input_path,
                metrics=QualityMetrics(),
                errors=[str(e)],
                processing_time=time.time() - start_time
            )

    def _convert_pdf_to_images(
        self,
        pdf_path: Path,
        start_page: int | None = None,
        end_page: int | None = None,
        scale: float = 2.0
    ) -> list[Path]:
        """Convert PDF pages to images."""
        self.console.print("📄 Converting PDF to images...")

        try:
            # Create output directory
            output_dir = pdf_path.parent / f"{pdf_path.stem}_images"
            output_dir.mkdir(exist_ok=True)

            # Convert pages
            images = convert_from_path(
                pdf_path,
                first_page=start_page,
                last_page=end_page,
                dpi=int(150 * scale),
                fmt="PNG"
            )

            image_paths = []
            for i, image in enumerate(images):
                page_num = (start_page or 1) + i
                image_path = output_dir / f"page_{page_num:03d}.png"
                image.save(image_path, "PNG")
                image_paths.append(image_path)

            self.console.print(f"✅ Converted {len(image_paths)} pages")
            return image_paths

        except (OSError, ValueError, RuntimeError) as e:
            self.console.print(f"❌ PDF conversion failed: {e}", style="red")
            return []

    def _process_images_in_batches(
        self,
        image_paths: list[Path],
        profile: Any
    ) -> list[dict[str, Any]]:
        """Process images in batches using the specified profile."""
        batch_size = profile.batch_size
        batch_results = []

        with Progress() as progress:
            task = progress.add_task("Processing batches...", total=len(image_paths))

            for i in range(0, len(image_paths), batch_size):
                batch_images = image_paths[i:i + batch_size]
                batch_num = (i // batch_size) + 1

                try:
                    # Prepare images for Gemini
                    pil_images = [Image.open(img_path) for img_path in batch_images]

                    # Create prompt with profile instructions
                    prompt_parts = [profile.system_prompt]
                    prompt_parts.extend(pil_images)

                    # Process with Gemini
                    assert self.model is not None
                    response = self.model.generate_content(prompt_parts)

                    if response.text:
                        batch_results.append({
                            "batch_num": batch_num,
                            "pages": [p.name for p in batch_images],
                            "text": response.text,
                            "page_count": len(batch_images)
                        })
                        self.console.print(f"✅ Batch {batch_num} complete")
                    else:
                        self.console.print(f"⚠️ Batch {batch_num} returned empty", style="yellow")

                except (OSError, ValueError, RuntimeError) as e:
                    self.console.print(f"❌ Batch {batch_num} failed: {e}", style="red")
                    batch_results.append({
                        "batch_num": batch_num,
                        "error": str(e),
                        "pages": [p.name for p in batch_images]
                    })

                progress.advance(task, len(batch_images))

        return batch_results

    def _combine_batch_results(self, batch_results: list[dict[str, Any]]) -> str:
        """Combine text from all successful batches."""
        texts = []
        for batch in batch_results:
            if "text" in batch and batch["text"]:
                texts.append(batch["text"])

        return "\\n\\n".join(texts)

    def _save_results(
        self,
        final_text: str,
        input_path: Path,
        output_path: Path | None,
        profile: Any,
        metrics: QualityMetrics,
        batch_results: list[dict[str, Any]]
    ) -> Path:
        """Save processing results to files."""
        # Determine output path
        if output_path is None:
            output_path = input_path.parent / f"{input_path.stem}_processed.md"

        # Save final markdown
        output_path.write_text(final_text, encoding="utf-8")

        # Save processing metadata
        metadata = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "input_file": str(input_path),
            "output_file": str(output_path),
            "profile": {
                "name": profile.name,
                "document_type": profile.document_type,
                "model": profile.model_name
            },
            "metrics": metrics.model_dump(),
            "batch_results": batch_results
        }

        metadata_path = output_path.with_suffix(".json")
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        return output_path

    def _display_results(self, result: ProcessingResult) -> None:
        """Display processing results in a nice table."""
        table = Table(title="Processing Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Success", "✅ Yes" if result.success else "❌ No")
        table.add_row("Quality Score", f"{result.metrics.calculate_score():.1f}")
        table.add_row("Processing Time", f"{result.processing_time:.1f}s")
        table.add_row("Pages Processed", str(result.metrics.pages_processed))
        table.add_row("Paragraphs Merged", str(result.metrics.paragraphs_merged))
        table.add_row("Headers Removed", str(result.metrics.headers_removed))
        table.add_row("Lines Processed", str(result.metrics.lines_processed))

        if result.output_path:
            table.add_row("Output File", str(result.output_path.name))

        self.console.print(table)

    def process_batch(self, request: BatchProcessingRequest) -> list[ProcessingResult]:
        """Process multiple documents in batch."""
        # Find all matching files
        files: list[Path] = []
        for pattern in request.file_patterns:
            if request.recursive:
                files.extend(request.input_directory.rglob(pattern))
            else:
                files.extend(request.input_directory.glob(pattern))

        self.console.print(f"\\n📁 Found {len(files)} files to process")

        results = []
        for pdf_file in files:
            output_path = request.output_directory / f"{pdf_file.stem}_processed.md"

            processing_request = ProcessingRequest(
                input_path=pdf_file,
                output_path=output_path,
                profile=request.profile
            )

            result = self.process_document(processing_request)
            results.append(result)

        # Display batch summary
        self._display_batch_summary(results)
        return results

    def _display_batch_summary(self, results: list[ProcessingResult]) -> None:
        """Display summary of batch processing results."""
        successful = sum(1 for r in results if r.success)
        total_time = sum(r.processing_time for r in results)
        avg_quality = sum(r.metrics.calculate_score() for r in results) / len(results)

        table = Table(title="Batch Processing Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Total Files", str(len(results)))
        table.add_row("Successful", f"{successful}/{len(results)}")
        table.add_row("Success Rate", f"{successful/len(results)*100:.1f}%")
        table.add_row("Total Time", f"{total_time:.1f}s")
        table.add_row("Average Quality", f"{avg_quality:.1f}")

        self.console.print(table)
