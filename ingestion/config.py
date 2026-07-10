"""Configuration for the AEMO ingestion pipeline.

Covers what to pull (date range, NEM region), where NEMweb reports live
(see docs/adr/0001-aemo-data-access.md), where to land output, and env
var / logging setup. No network or parsing logic here.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

NEM_REGIONS = {"NSW1", "QLD1", "SA1", "TAS1", "VIC1"}

NEMWEB_BASE_URL = "https://nemweb.com.au"
NEMWEB_CURRENT_PATH = "/Reports/CURRENT"
NEMWEB_ARCHIVE_PATH = "/Reports/ARCHIVE"

# Fixed, non-dated reference file: DUID -> region -> fuel type -> emissions factor.
CDEII_REFERENCE_PATH = "/Reports/CURRENT/CDEII/CO2EII_AVAILABLE_GENERATORS.CSV"


@dataclass(frozen=True)
class ReportSource:
    """Location and filename pattern for one AEMO time-series report type."""

    name: str
    folder: str  # e.g. "DispatchIS_Reports"
    filename_prefix: str  # e.g. "PUBLIC_DISPATCHIS"


REPORT_SOURCES: dict[str, ReportSource] = {
    "dispatch_price": ReportSource(
        name="dispatch_price",
        folder="DispatchIS_Reports",
        filename_prefix="PUBLIC_DISPATCHIS",
    ),
    "dispatch_scada": ReportSource(
        name="dispatch_scada",
        folder="Dispatch_SCADA",
        filename_prefix="PUBLIC_DISPATCHSCADA",
    ),
}


def _default_landing_path() -> Path:
    return Path(os.getenv("DATA_LANDING_PATH", "./data/landing")).resolve()


def _default_log_level() -> str:
    return os.getenv("LOG_LEVEL", "INFO").upper()


@dataclass
class IngestionConfig:
    """Config for a single ingestion run: date range, regions, and landing path.

    Region filtering happens downstream (dispatch reports cover all regions
    in one file); this just records which regions the run cares about.
    """

    start_date: date
    end_date: date
    regions: tuple[str, ...]
    landing_path: Path = field(default_factory=_default_landing_path)
    log_level: str = field(default_factory=_default_log_level)

    def __post_init__(self) -> None:
        if self.start_date > self.end_date:
            raise ValueError(
                f"start_date ({self.start_date}) must not be after end_date ({self.end_date})"
            )

        if not self.regions:
            raise ValueError("At least one NEM region must be specified")

        unknown = set(self.regions) - NEM_REGIONS
        if unknown:
            raise ValueError(
                f"Unknown NEM region(s): {sorted(unknown)}. Valid regions: {sorted(NEM_REGIONS)}"
            )

    @classmethod
    def from_args(cls, start: str, end: str, regions: list[str] | str) -> IngestionConfig:
        """Build a config from CLI-style string args (YYYY-MM-DD dates, region code(s))."""
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date()

        if isinstance(regions, str):
            region_list = [r.strip().upper() for r in regions.split(",") if r.strip()]
        else:
            region_list = [r.strip().upper() for r in regions]

        return cls(start_date=start_date, end_date=end_date, regions=tuple(region_list))


def configure_logging(level: str | None = None) -> None:
    """Configure root logging for the ingestion package. Call once at process start."""
    logging.basicConfig(
        level=level or _default_log_level(),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
