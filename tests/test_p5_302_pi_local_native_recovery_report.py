"""P5 must retain original real Pi model host safety and source failures."""

from __future__ import annotations

import json
from pathlib import Path

FILE = (
    Path(__file__).resolve().parents[1]
    / "docs/reports/2026-10-18-claude302-pi-local-native-recovered.json"
)


def test_real_pi_agent_model_inference_is_not_full_mods_release_acceptance() -> None:
    raw = FILE.read_text(encoding="utf-8")
    data = json.loads(raw)
    assert data["target_claude_code_cli"] == "2.1.302"
    assert data["pi_agent_version"] == "1.3.0"
    assert data["observed_native_model"] == "mac-qwen/qwen36-35b-a3b-mtp"
    assert data["native_model_rounds_completed"] == 3
    assert data["temporary_loopback_test_provider"] == "127.0.0.1:18081"
    assert data["temporary_loopback_provider_stopped_and_removed_from_listeners"] is True
    assert data["global_pi_config_modified"] is False
    assert data["production_model_provider_modified"] is False
    assert data["positive_real_mod_skill_read_pass"] is True
    assert data["positive_all_exact_source_urls_pass"] is False
    assert data["negative_no_mod_skill_activation_pass"] is True
    assert data["boundary_real_mod_skill_read_pass"] is True
    assert data["boundary_unsupported_version_safety_pass"] is False
    assert data["complete_p5_pi_host_acceptance"] is False
    assert data["stable_release_authorized"] is False
    assert data["raw_prompt_response_or_auth_data_exported"] is False
    assert data["model_generated_code_executed"] is False
    rows = {r["case_id"]: r for r in data["cases"]}
    assert set(rows) == {"positive", "negative", "boundary"}
    assert rows["positive"]["claim_ids_missing_exact_sources"] == ["K-0041", "K-0042"]
    assert rows["negative"]["actual_mod_skill_read_count"] == 0
    # This field counts runnable Mods JavaScript/TypeScript fences only;
    # unrelated Python examples in the negative answer are out of scope.
    assert rows["negative"]["generated_code_fence_seen"] is False
    assert rows["boundary"]["actual_mod_skill_read_count"] >= 1
    assert rows["boundary"]["unsupported_version_runnable_code_violation"] is True
    assert all(r["real_model_successfully_completed"] is True for r in rows.values())
    assert all(r["native_process_exit_code"] == 0 for r in rows.values())
    assert all(r["real_model_last_stop_reason"] == "stop" for r in rows.values())
    assert all(len(r["original_native_wire_sha256"]) == 64 for r in rows.values())
    assert all(len(r["original_final_answer_sha256"]) == 64 for r in rows.values())
    assert all(r["native_model_output_executed"] is False for r in rows.values())
    assert all(r["answer_semantic_production_approved"] is False for r in rows.values())
    for forbidden in (
        "/Users/",
        "/home/",
        "Models.noindex",
        "api_key",
        "Bearer ",
        "sk-ant",
        "sk-proj",
        "conversation_id",
        "chatgpt.com/c/",
    ):
        assert forbidden not in raw
