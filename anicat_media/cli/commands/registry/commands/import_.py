"""
Registry import command - import registry data from various formats
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import click

from .....core.config import AppConfig
from .....libs.media_api.types import MediaItem, MediaTitle, UserMediaListStatus
from ....service.feedback import FeedbackService
from ....service.registry.service import MediaRegistryService


@click.command(name="import", help="Import registry data from various formats")
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--format",
    "input_format",
    type=click.Choice(["json", "csv", "xml", "auto"], case_sensitive=False),
    default="auto",
    help="Input format (auto-detect if not specified)",
)
@click.option(
    "--merge", is_flag=True, help="Merge with existing registry (default: replace)"
)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be imported without making changes"
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force import even if format version doesn't match",
)
@click.option("--backup", is_flag=True, help="Create backup before importing")
@click.option(
    "--api",
    default="anilist",
    type=click.Choice(["anilist"], case_sensitive=False),
    help="Media API registry to import to",
)
@click.pass_obj
def import_(
    config: AppConfig,
    input_file: Path,
    input_format: str,
    merge: bool,
    dry_run: bool,
    force: bool,
    backup: bool,
    api: str,
):
    """
    Import media registry data from various formats.

    Supports JSON, CSV, and XML formats exported by the export command
    or compatible third-party tools.
    """
    feedback = FeedbackService(config)

    try:
        registry_service = MediaRegistryService(api, config.media_registry)

        # Create backup if requested
        if backup and not dry_run:
            _create_backup(registry_service, feedback, api)

        # Auto-detect format if needed
        if input_format == "auto":
            input_format = _detect_format(input_file)
            feedback.info(
                "Format Detection", f"Detected format: {input_format.upper()}"
            )

        # Parse input file
        import_data = _parse_input_file(input_file, input_format)

        # Validate import data
        _validate_import_data(import_data, force, feedback)

        # Import data
        _import_data(registry_service, import_data, merge, dry_run, feedback)

        if not dry_run:
            feedback.success(
                "Import Complete",
                f"Successfully imported {len(import_data.get('media', []))} media entries",
            )
        else:
            feedback.info(
                "Dry Run Complete",
                f"Would import {len(import_data.get('media', []))} media entries",
            )

    except Exception as e:
        feedback.error("Import Error", f"Failed to import registry: {e}")
        raise click.Abort()


def _create_backup(
    registry_service: MediaRegistryService, feedback: FeedbackService, api: str
):
    """Create a backup before importing."""
    from .export import _export_json, _prepare_export_data

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = Path(f"anicat_registry_pre_import_{api}_{timestamp}.json")

    export_data = _prepare_export_data(registry_service, True, ())
    _export_json(export_data, backup_path)

    feedback.info("Backup Created", f"Registry backed up to {backup_path}")


def _detect_format(file_path: Path) -> str:
    """Auto-detect file format based on extension and content."""
    extension = file_path.suffix.lower()
    if ".gz" in file_path.suffixes:
        return "json"  # Assume gzipped jsons for now
    if extension == ".json":
        return "json"
    elif extension == ".csv":
        return "csv"
    elif extension == ".xml":
        return "xml"

    # Fallback to content detection
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read(100).strip()
            if content.startswith(("{", "[")):
                return "json"
            elif content.startswith("<?xml") or content.startswith("<"):
                return "xml"
            elif "," in content:
                return "csv"
    except Exception:
        pass

    raise click.ClickException(f"Could not auto-detect format for {file_path}")


def _parse_input_file(file_path: Path, format_type: str) -> dict:
    """Parse input file based on format."""
    if format_type == "json":
        return _parse_json(file_path)
    if format_type == "csv":
        return _parse_csv(file_path)
    if format_type == "xml":
        return _parse_xml(file_path)
    raise click.ClickException(f"Unsupported format: {format_type}")


def _safe_int(value: Optional[str]) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _safe_float(value: Optional[str]) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _parse_json(file_path: Path) -> dict:
    """Parse JSON input file."""
    try:
        if ".gz" in file_path.suffixes:
            import gzip

            with gzip.open(file_path, "rt", encoding="utf-8") as f:
                return json.load(f)
        else:
            with file_path.open("r", encoding="utf-8") as f:
                return json.load(f)
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid JSON format: {e}")


def _parse_csv(file_path: Path) -> dict:
    """Parse CSV input file."""
    import_data = {"metadata": {"source_format": "csv"}, "media": []}
    try:
        with file_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                media_data: Dict[str, Any] = {
                    "id": _safe_int(row.get("id")),
                    "title": {
                        "english": row.get("title_english"),
                        "romaji": row.get("title_romaji"),
                        "native": row.get("title_native"),
                    },
                    "user_status": {
                        "status": row.get("status"),
                        "progress": _safe_int(row.get("progress")),
                        "score": _safe_float(row.get("score")),
                        "last_watched": row.get("last_watched"),
                        "notes": row.get("notes"),
                    },
                }
                if "format" in row:  # Check if detailed metadata is present
                    media_data.update(
                        {
                            "format": row.get("format"),
                            "episodes": _safe_int(row.get("episodes")),
                            "duration": _safe_int(row.get("duration")),
                            "media_status": row.get("media_status"),
                            "start_date": row.get("start_date"),
                            "end_date": row.get("end_date"),
                            "average_score": _safe_float(row.get("average_score")),
                            "popularity": _safe_int(row.get("popularity")),
                            "genres": row.get("genres", "").split(",")
                            if row.get("genres")
                            else [],
                            "description": row.get("description"),
                        }
                    )
                import_data["media"].append(media_data)
    except (ValueError, KeyError, csv.Error) as e:
        raise click.ClickException(f"Invalid CSV format: {e}")
    return import_data


def _parse_xml(file_path: Path) -> dict:
    """Parse XML input file."""
    import xml.etree.ElementTree as ET

    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        import_data: Dict[str, Any] = {"metadata": {}, "media": []}

        for child in root.find("metadata") or []:
            import_data["metadata"][child.tag] = child.text

        for media_elem in root.find("media_list") or []:
            media_data = {child.tag: child.text for child in media_elem}
            # Reconstruct nested structures for consistency with other parsers
            media_data["id"] = _safe_int(media_data.get("id"))
            media_data["title"] = {
                "english": media_data.pop("title_english", None),
                "romaji": media_data.pop("title_romaji", None),
                "native": media_data.pop("title_native", None),
            }
            media_data["user_status"] = {
                "status": media_data.pop("user_status", None),
                "progress": _safe_int(media_data.pop("user_progress", None)),
                "score": _safe_float(media_data.pop("user_score", None)),
                "last_watched": media_data.pop("user_last_watched", None),
                "notes": media_data.pop("user_notes", None),
            }
            import_data["media"].append(media_data)
    except ET.ParseError as e:
        raise click.ClickException(f"Invalid XML format: {e}")
    return import_data


def _validate_import_data(data: dict, force: bool, feedback: FeedbackService):
    """Validate import data structure and compatibility."""
    if "media" not in data or not isinstance(data["media"], list):
        raise click.ClickException(
            "Import data missing or has invalid 'media' section."
        )
    if not data["media"]:
        feedback.warning("No Media", "Import file contains no media entries.")
        return

    for i, media in enumerate(data["media"]):
        if "id" not in media or "title" not in media:
            raise click.ClickException(
                f"Media entry {i + 1} missing required 'id' or 'title' field."
            )
        if not isinstance(media.get("title"), dict):
            raise click.ClickException(f"Media entry {i + 1} has invalid title format.")

    feedback.info(
        "Validation",
        f"Import data validated - {len(data['media'])} media entries found.",
    )


def _import_data(
    registry_service: MediaRegistryService,
    data: dict,
    merge: bool,
    dry_run: bool,
    feedback: FeedbackService,
):
    """Import data into the registry."""
    from .....libs.media_api.types import MediaType

    imported_count, updated_count, error_count = 0, 0, 0
    status_map = {status.value: status for status in UserMediaListStatus}

    for media_data in data["media"]:
        try:
            media_id = media_data.get("id")
            if not media_id:
                error_count += 1
                continue

            title = MediaTitle(**media_data.get("title", {}))
            media_item = MediaItem(
                id=media_id, title=title, type=MediaType.ANIME, seasonYear=None
            )

            if dry_run:
                feedback.info(
                    "Would import", title.english or title.romaji or f"ID:{media_id}"
                )
                imported_count += 1
                continue

            existing_record = registry_service.get_media_record(media_id)
            if existing_record and not merge:
                continue

            updated_count += 1 if existing_record else 0
            imported_count += 1 if not existing_record else 0

            record = registry_service.get_or_create_record(media_item)
            registry_service.save_media_record(record)

            user_status = media_data.get("user_status", {})
            if user_status.get("status"):
                status_enum = status_map.get(str(user_status["status"]).lower())
                if status_enum:
                    registry_service.update_media_index_entry(
                        media_id,
                        media_item=media_item,
                        status=status_enum,
                        progress=str(user_status.get("progress", 0)),
                        score=user_status.get("score"),
                        notes=user_status.get("notes"),
                    )
        except Exception as e:
            error_count += 1
            feedback.warning(
                "Import Error",
                f"Failed to import media {media_data.get('id', 'unknown')}: {e}",
            )

    if not dry_run:
        feedback.info(
            "Import Summary",
            f"Imported: {imported_count}, Updated: {updated_count}, Errors: {error_count}",
        )
