"""Fail-closed exceptions for SSOT source ingestion."""


class RegistryError(ValueError):
    """A source registry violates schema or provenance policy."""


class CollectionError(RuntimeError):
    """A document fetch or snapshot persistence is unsafe or incomplete."""


class ClaimError(ValueError):
    """A Knowledge Claim or its decision history violates evidence policy."""
