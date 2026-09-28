"""Accepted media v1 domain types; production admits only reviewed references.

No persistence, acquisition, permission grant, or publication API lives here.
V0 classes and their serialized shape remain unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .schema import CanonicalRecords, Source, Observation

Certainty = Literal["exact", "asserted", "approximate"]
Modality = Literal["visual", "ocr", "transcription", "location_inference", "metadata"]


@dataclass(frozen=True)
class Basis:
    kind: Literal["statement", "finding", "source", "clock", "unknown"]
    ref: str | None


@dataclass(frozen=True)
class UnknownTime:
    kind: Literal["unknown"]
    certainty: Literal["unknown"]
    basis: Basis


@dataclass(frozen=True)
class InstantTime:
    kind: Literal["instant"]
    value: str
    certainty: Certainty
    basis: Basis


@dataclass(frozen=True)
class DateTimeValue:
    kind: Literal["date"]
    value: str
    certainty: Certainty
    basis: Basis


@dataclass(frozen=True)
class TimeRange:
    kind: Literal["range"]
    start: str
    end: str
    precision: Literal["date", "instant"]
    certainty: Certainty
    basis: Basis


@dataclass(frozen=True)
class EntityLocation:
    kind: Literal["entity"]
    entity_id: str


@dataclass(frozen=True)
class RegionLocation:
    kind: Literal["region"]
    label: str


@dataclass(frozen=True)
class PointLocation:
    kind: Literal["point"]
    latitude: float
    longitude: float


@dataclass(frozen=True)
class Location:
    basis_kind: Literal["author_labeled", "visible_sign", "corroborated", "exif_permitted", "inferred", "unresolved"]
    value: EntityLocation | RegionLocation | PointLocation | None
    precision_m: int | None
    generalization: Literal["exact", "generalized", "withheld", "unknown"]
    sensitivity: Literal["nonsensitive", "sensitive", "unassessed"]
    basis: Basis
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class WholeImage:
    kind: Literal["whole"]


@dataclass(frozen=True)
class ImageRegion:
    kind: Literal["image_region"]
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class TimeSelector:
    kind: Literal["time_range"]
    start_ms: int
    end_ms: int


@dataclass(frozen=True)
class FrameSelector:
    kind: Literal["frames"]
    timestamps_ms: tuple[int, ...]


@dataclass(frozen=True)
class Target:
    media_version_id: str
    source_attachment_id: str
    selector: WholeImage | ImageRegion | TimeSelector | FrameSelector


@dataclass(frozen=True)
class Dimensions:
    width: int
    height: int


@dataclass(frozen=True)
class Speaker:
    role: Literal["author", "commenter", "unknown"]
    attribution: str | None


@dataclass(frozen=True)
class Analyst:
    kind: Literal["human", "tool", "model"]
    label: str
    version: str


@dataclass(frozen=True)
class Method:
    name: str
    version: str
    configuration_summary: str


@dataclass(frozen=True)
class Origin:
    kind: Literal["statement", "finding"]
    id: str


@dataclass(frozen=True)
class MediaAsset:
    id: str
    state: Literal["active"]
    origin_asset_id: str | None
    origin_statement_id: str | None


@dataclass(frozen=True)
class MediaVersion:
    id: str
    state: Literal["active"]
    asset_id: str
    media_type: Literal["image", "video", "audio"]
    dimensions: Dimensions | None
    duration_ms: int | None
    retrieval_time: QualifiedTime
    identity_basis: Literal["permitted_digest", "provider_version", "reviewed_copy", "unverifiable"]
    reproducibility: Literal["bounded", "unavailable"]
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class AvailabilityReport:
    id: str
    state: Literal["active"]
    media_version_id: str
    checked_at: QualifiedTime
    availability: Literal["available", "unavailable", "unknown"]
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class SourceAttachment:
    id: str
    state: Literal["active"]
    source_id: str
    asset_id: str
    media_version_id: str
    ordinal: int | None
    ordinal_basis: Literal["source_order", "unknown"]
    publication_time: QualifiedTime
    association_observed_time: QualifiedTime


@dataclass(frozen=True)
class AttributedStatement:
    id: str
    state: Literal["active"]
    source_id: str
    statement_kind: Literal["caption", "comment", "correction", "clarification"]
    speaker: Speaker
    text: str
    publication_time: QualifiedTime
    corrects_statement_id: str | None


@dataclass(frozen=True)
class StatementMapping:
    id: str
    state: Literal["active"]
    statement_id: str
    mapping_kind: Literal["single", "multiple", "ordered_item", "ambiguous"]
    attachment_ids: tuple[str, ...]
    list_item: int | None
    basis: str
    certainty: Literal["explicit", "ambiguous", "unresolved"]


@dataclass(frozen=True)
class AnalysisRun:
    id: str
    state: Literal["active"]
    source_id: str
    inputs: tuple[Target, ...]
    analyst: Analyst
    method: Method
    analysis_time: QualifiedTime
    modalities: tuple[Modality, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class AnalysisFinding:
    id: str
    state: Literal["active"]
    run_id: str
    target: Target
    modality: Modality
    metadata_fields: tuple[Literal["capture_time", "gps"], ...]
    content: str
    certainty: Literal["observed", "asserted", "inferred", "unresolved"]
    corroborating_evidence_ids: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class ReviewedSelection:
    id: str
    state: Literal["active"]
    origin: Origin
    mapping_id: str | None
    media_version_ids: tuple[str, ...]
    reviewer_role: Literal["maintainer"]
    reviewed_at: QualifiedTime
    change_set_id: str


@dataclass(frozen=True)
class ObservationProvenance:
    id: str
    state: Literal["active"]
    observation_id: str
    selection_id: str
    event_times: tuple[QualifiedTime, ...]
    locations: tuple[Location, ...]


@dataclass(frozen=True)
class LegacyArtifactMapping:
    id: str
    state: Literal["active"]
    observation_id: str
    artifact_ref_index: int
    asset_id: str
    media_version_id: str
    reviewed_selection_id: str
    migration_id: str


QualifiedTime = UnknownTime | InstantTime | DateTimeValue | TimeRange


@dataclass(frozen=True)
class MediaTombstone:
    id: str
    state: Literal["removed", "redacted"]
    reason_code: Literal["privacy_removal", "retention_expired", "source_withdrawn"]


@dataclass(frozen=True, kw_only=True)
class MediaSource(Source):
    source_role: Literal["original", "comment", "analysis_report"]


@dataclass(frozen=True, kw_only=True)
class MediaObservation(Observation):
    origin_kind: Literal["source_text", "media_statement", "media_analysis"]
    provenance_id: str | None


@dataclass
class MediaRecords(CanonicalRecords):
    """Typed v1 collections; eligibility/support remain the shared service responsibility."""
    media_assets: list[MediaAsset | MediaTombstone] = field(default_factory=list)
    media_versions: list[MediaVersion | MediaTombstone] = field(default_factory=list)
    availability_reports: list[AvailabilityReport | MediaTombstone] = field(default_factory=list)
    source_attachments: list[SourceAttachment | MediaTombstone] = field(default_factory=list)
    attributed_statements: list[AttributedStatement | MediaTombstone] = field(default_factory=list)
    statement_mappings: list[StatementMapping | MediaTombstone] = field(default_factory=list)
    analysis_runs: list[AnalysisRun | MediaTombstone] = field(default_factory=list)
    analysis_findings: list[AnalysisFinding | MediaTombstone] = field(default_factory=list)
    reviewed_selections: list[ReviewedSelection | MediaTombstone] = field(default_factory=list)
    observation_provenance: list[ObservationProvenance | MediaTombstone] = field(default_factory=list)
    legacy_artifact_mappings: list[LegacyArtifactMapping | MediaTombstone] = field(default_factory=list)


MEDIA_SPECS = {
    "media_asset": ("media_assets", "id", MediaAsset),
    "media_version": ("media_versions", "id", MediaVersion),
    "availability_report": ("availability_reports", "id", AvailabilityReport),
    "source_attachment": ("source_attachments", "id", SourceAttachment),
    "attributed_statement": ("attributed_statements", "id", AttributedStatement),
    "statement_mapping": ("statement_mappings", "id", StatementMapping),
    "analysis_run": ("analysis_runs", "id", AnalysisRun),
    "analysis_finding": ("analysis_findings", "id", AnalysisFinding),
    "reviewed_selection": ("reviewed_selections", "id", ReviewedSelection),
    "observation_provenance": ("observation_provenance", "id", ObservationProvenance),
    "legacy_artifact_mapping": ("legacy_artifact_mappings", "id", LegacyArtifactMapping),
}
