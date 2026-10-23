---
name: mods-qa-widget-check
description: Read-only QA recipe for reviewing or verifying changes to packages/widget. When changes under packages/widget are under review or verification, use this package-specific skill to learn expected behavior.
---
# Widget package verification and review recipe
Use only when verifying or reviewing changed files in packages/widget.

The expected behavior is that add(a,b) returns exactly a+b. For a safe mental check,
add(2,3) must equal 5. Do not write or change any files. The unique reference marker is:
WIDGET_AUDIT_RECIPE_BRINE_63821

When done, explain whether the modified package breaks this invariant.
