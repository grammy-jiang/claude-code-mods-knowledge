# Offline CI installation permission boundary

QA script: scripts/ci_offline.sh; workflow template: docs/operations/qa-workflow-template.yml.

Current GitHub OAuth credential lacks permission to push .github/workflows/ paths.
GitHub rejected that update on 2026-10-14. Do not bypass this control.
An authorized GitHub workflow-write credential may review and copy the template
into .github/workflows/qa.yml later. Until then, run model-free checks on three
hosts with MODS_PYTHON_VERSION=3.11 bash scripts/ci_offline.sh.
