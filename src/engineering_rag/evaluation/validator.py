"""Validate Golden Dataset targets against the exact Chunk collection."""

from __future__ import annotations

import json
from difflib import get_close_matches
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from engineering_rag.evaluation.dataset import GoldenDataset, RelevanceTarget
from engineering_rag.models import Chunk


class ValidationStatus(str, Enum):
    VALID = "VALID"
    DOCUMENT_NOT_FOUND = "DOCUMENT_NOT_FOUND"
    CLAUSE_NOT_FOUND = "CLAUSE_NOT_FOUND"
    SOURCE_NOT_FOUND = "SOURCE_NOT_FOUND"
    EXPLANATION_MISMATCH = "EXPLANATION_MISMATCH"
    CONTENT_TYPE_MISMATCH = "CONTENT_TYPE_MISMATCH"
    AMBIGUOUS_TARGET = "AMBIGUOUS_TARGET"
    DUPLICATE_TARGET = "DUPLICATE_TARGET"
    INVALID_RELEVANCE = "INVALID_RELEVANCE"


class TargetValidation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_id: str
    target_index: int = Field(ge=0)
    target: RelevanceTarget
    status: ValidationStatus
    reason: str
    matching_chunk_ids: list[str] = Field(default_factory=list)
    matching_logical_ids: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class ValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_version: str
    total_queries: int = Field(ge=0)
    total_targets: int = Field(ge=0)
    valid_targets: int = Field(ge=0)
    invalid_targets: int = Field(ge=0)
    valid_target_coverage: float = Field(ge=0, le=1)
    is_valid: bool
    results: list[TargetValidation] = Field(default_factory=list)


class GoldenDatasetValidator:
    """Check that every judgment resolves to one stable logical source."""

    def validate(
        self, dataset: GoldenDataset, chunks: list[Chunk]
    ) -> ValidationReport:
        documents = sorted({chunk.document_id for chunk in chunks})
        by_document: dict[str, list[Chunk]] = {
            document_id: [
                chunk for chunk in chunks if chunk.document_id == document_id
            ]
            for document_id in documents
        }
        results: list[TargetValidation] = []
        for query in dataset.queries:
            seen_targets: set[tuple[object, ...]] = set()
            for target_index, target in enumerate(query.relevant):
                identity = _target_identity(target)
                if identity in seen_targets:
                    results.append(
                        TargetValidation(
                            query_id=query.query_id,
                            target_index=target_index,
                            target=target,
                            status=ValidationStatus.DUPLICATE_TARGET,
                            reason="The same logical relevance target is annotated more than once.",
                        )
                    )
                    continue
                seen_targets.add(identity)
                results.append(
                    self._validate_target(
                        query.query_id,
                        target_index,
                        target,
                        documents,
                        by_document,
                    )
                )

        valid_targets = sum(
            result.status == ValidationStatus.VALID for result in results
        )
        total_targets = len(results)
        return ValidationReport(
            dataset_version=dataset.version,
            total_queries=len(dataset.queries),
            total_targets=total_targets,
            valid_targets=valid_targets,
            invalid_targets=total_targets - valid_targets,
            valid_target_coverage=(valid_targets / total_targets if total_targets else 0),
            is_valid=valid_targets == total_targets and total_targets > 0,
            results=results,
        )

    def _validate_target(
        self,
        query_id: str,
        target_index: int,
        target: RelevanceTarget,
        documents: list[str],
        by_document: dict[str, list[Chunk]],
    ) -> TargetValidation:
        if target.relevance not in (0, 1, 2):
            return self._result(
                query_id,
                target_index,
                target,
                ValidationStatus.INVALID_RELEVANCE,
                "relevance must be 0, 1, or 2.",
            )
        if target.document_id not in by_document:
            return self._result(
                query_id,
                target_index,
                target,
                ValidationStatus.DOCUMENT_NOT_FOUND,
                f"document_id '{target.document_id}' does not exist in the Chunk collection.",
                suggestions=[f"Available document_id: {value}" for value in documents],
            )

        document_chunks = by_document[target.document_id]
        if target.clause_number:
            locator_matches = [
                chunk
                for chunk in document_chunks
                if chunk.clause_number == target.clause_number
            ]
            if not locator_matches:
                clauses = sorted(
                    {
                        chunk.clause_number
                        for chunk in document_chunks
                        if chunk.clause_number
                    }
                )
                close = get_close_matches(
                    target.clause_number, clauses, n=5, cutoff=0.6
                )
                return self._result(
                    query_id,
                    target_index,
                    target,
                    ValidationStatus.CLAUSE_NOT_FOUND,
                    f"clause_number '{target.clause_number}' was not found in the "
                    "specified document.",
                    suggestions=[f"Nearby clause_number: {value}" for value in close],
                )
        else:
            locator_matches = self._fallback_locator_matches(target, document_chunks)
            if not locator_matches:
                return self._result(
                    query_id,
                    target_index,
                    target,
                    ValidationStatus.SOURCE_NOT_FOUND,
                    "The logical_chunk_id or source_block_ids locator was not found.",
                )

        explanation_matches = [
            chunk
            for chunk in locator_matches
            if chunk.is_explanation == target.is_explanation
        ]
        if not explanation_matches:
            available = sorted({chunk.is_explanation for chunk in locator_matches})
            return self._result(
                query_id,
                target_index,
                target,
                ValidationStatus.EXPLANATION_MISMATCH,
                "The locator exists, but its is_explanation value does not match.",
                suggestions=[f"Available is_explanation: {value}" for value in available],
            )

        content_matches = explanation_matches
        if target.content_type:
            content_matches = [
                chunk
                for chunk in explanation_matches
                if chunk.content_type == target.content_type
            ]
            if not content_matches:
                available = sorted(
                    {chunk.content_type for chunk in explanation_matches}
                )
                return self._result(
                    query_id,
                    target_index,
                    target,
                    ValidationStatus.CONTENT_TYPE_MISMATCH,
                    "The locator exists, but its content_type does not match.",
                    suggestions=[f"Available content_type: {value}" for value in available],
                )

        logical_ids = sorted(
            {
                chunk.logical_chunk_id or _source_identity(chunk)
                for chunk in content_matches
            }
        )
        if len(logical_ids) > 1:
            return self._result(
                query_id,
                target_index,
                target,
                ValidationStatus.AMBIGUOUS_TARGET,
                "The target resolves to multiple logical sources.",
                chunks=content_matches,
                logical_ids=logical_ids,
            )
        return self._result(
            query_id,
            target_index,
            target,
            ValidationStatus.VALID,
            f"Matched {len(content_matches)} physical Chunk(s) to one logical source.",
            chunks=content_matches,
            logical_ids=logical_ids,
        )

    @staticmethod
    def _fallback_locator_matches(
        target: RelevanceTarget, chunks: list[Chunk]
    ) -> list[Chunk]:
        if target.logical_chunk_id:
            return [
                chunk
                for chunk in chunks
                if chunk.logical_chunk_id == target.logical_chunk_id
            ]
        expected = tuple(sorted(target.source_block_ids))
        return [
            chunk
            for chunk in chunks
            if tuple(sorted(chunk.source_block_ids)) == expected
        ]

    @staticmethod
    def _result(
        query_id: str,
        target_index: int,
        target: RelevanceTarget,
        status: ValidationStatus,
        reason: str,
        *,
        chunks: list[Chunk] | None = None,
        logical_ids: list[str] | None = None,
        suggestions: list[str] | None = None,
    ) -> TargetValidation:
        return TargetValidation(
            query_id=query_id,
            target_index=target_index,
            target=target,
            status=status,
            reason=reason,
            matching_chunk_ids=[chunk.chunk_id for chunk in chunks or []],
            matching_logical_ids=logical_ids or [],
            suggestions=suggestions or [],
        )


def write_validation_report(
    report: ValidationReport, output_dir: str | Path
) -> dict[str, Path]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "validation_report.json"
    markdown_path = destination / "validation_report.md"
    fixes_path = destination / "suggested_fixes.json"
    json_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(_render_markdown(report), encoding="utf-8")
    suggestions = [
        {
            "query_id": result.query_id,
            "target_index": result.target_index,
            "status": result.status.value,
            "suggestions": result.suggestions,
            "requires_human_review": True,
        }
        for result in report.results
        if result.status != ValidationStatus.VALID and result.suggestions
    ]
    fixes_path.write_text(
        json.dumps(suggestions, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "validation_json": json_path,
        "validation_markdown": markdown_path,
        "suggested_fixes": fixes_path,
    }


def _target_identity(target: RelevanceTarget) -> tuple[object, ...]:
    return (
        target.document_id,
        target.clause_number,
        target.is_explanation,
        target.content_type,
        target.logical_chunk_id,
        tuple(sorted(target.source_block_ids)),
    )


def _source_identity(chunk: Chunk) -> str:
    return "source:" + "|".join(sorted(chunk.source_block_ids))


def _render_markdown(report: ValidationReport) -> str:
    lines = [
        "# Golden Dataset validation",
        "",
        f"- Dataset version: `{report.dataset_version}`",
        f"- Total queries: {report.total_queries}",
        f"- Total targets: {report.total_targets}",
        f"- Valid targets: {report.valid_targets}",
        f"- Invalid targets: {report.invalid_targets}",
        f"- Valid target coverage: {report.valid_target_coverage:.2%}",
        f"- Status: `{'VALID' if report.is_valid else 'INVALID_GOLDEN_DATASET'}`",
        "",
        "## Invalid targets",
        "",
    ]
    invalid = [
        result for result in report.results if result.status != ValidationStatus.VALID
    ]
    if not invalid:
        lines.append("No invalid targets.")
    for result in invalid:
        lines.extend(
            [
                f"### {result.query_id} / target {result.target_index}",
                "",
                f"- Status: `{result.status.value}`",
                f"- Reason: {result.reason}",
                f"- Target: `{result.target.model_dump_json()}`",
            ]
        )
        lines.extend(f"- Possible clue: {value}" for value in result.suggestions)
        lines.append("")
    return "\n".join(lines) + "\n"
