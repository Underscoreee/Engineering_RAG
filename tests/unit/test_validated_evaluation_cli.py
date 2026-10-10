import json
import subprocess
import sys
from pathlib import Path

from engineering_rag.models import Chunk


def test_invalid_golden_dataset_blocks_scoring_before_elasticsearch(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "golden.json"
    chunks_path = tmp_path / "chunks.json"
    output_dir = tmp_path / "report"
    dataset_path.write_text(
        json.dumps(
            {
                "version": "invalid-v1",
                "queries": [
                    {
                        "query_id": "q1",
                        "query": "问题",
                        "query_type": "simple",
                        "relevant": [
                            {
                                "document_id": "wrong",
                                "clause_number": "1.0.1",
                                "relevance": 2,
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    chunks_path.write_text(
        "["
        + Chunk(
            chunk_id="c1",
            document_id="doc",
            content="content",
            page_start=1,
            page_end=1,
            clause_number="1.0.1",
            content_type="clause",
        ).model_dump_json()
        + "]",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/evaluate_retrieval.py",
            "--dataset",
            str(dataset_path),
            "--chunks",
            str(chunks_path),
            "--output-dir",
            str(output_dir),
            "--diagnostic",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert "INVALID_GOLDEN_DATASET" in completed.stderr
    status = json.loads(
        (output_dir / "diagnostic_status.json").read_text(encoding="utf-8")
    )
    assert status["baseline_status"] == "NOT_A_VALID_BASELINE"
    assert not (output_dir / "metrics.json").exists()
