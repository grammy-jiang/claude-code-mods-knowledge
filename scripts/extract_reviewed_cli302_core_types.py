#!/usr/bin/env python3
"""Extract ORIGINAL Claude Code 2.1.302 embedded core .d.ts, not old web types.

This does not execute a model, install a plugin, create a Claude session,
fetch documents, touch credentials, or publish a proprietary full declaration.
The Claude Code v2.1.302 official native binary contains a compressed core
declaration frame. Native Zstandard scans only that binary's frames and
requires an identical SHA256 of the decoded source on Mac ARM64 and Pi ARM64.
These declarations lack the dynamically merged built-in tool/MCP tables that
are written when a plugin loads; do NOT certify complete host type support.
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import hashlib
import mmap
from pathlib import Path

TARGET_CLI = "2.1.302"
DECLARATION_SHA256 = "8afa71883ecfa52901eb7a04cf31fef700d8ba565eaad244f4884cc620f8d56e"
DECLARATION_BYTES = 651_852
OFFICIAL_NATIVE_BINARIES = frozenset(
    (
        # Installed local MacBook Pro CLI 2.1.302
        "5262ce9de86243fed0d21edc39b271555d56780d0112e2b194439fe1c6662d37",
        # Installed Raspberry Pi CLI 2.1.302
        "2bd4f4e5ed5cb09955b490098f745321cb5491e7ea8c752ba1e3bb010cdadb10",
    )
)
ZSTD_MAGIC = bytes.fromhex("28b52ffd")
MAX_FRAME_BYTES = 16_000_000
MAX_DECLARATION_BYTES = 4_000_000


class CliTypesBlocked(ValueError):
    """Refuse an unverified target type declaration source."""


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def verify_core(raw: bytes) -> None:
    if (
        not isinstance(raw, bytes)
        or len(raw) != DECLARATION_BYTES
        or digest(raw) != DECLARATION_SHA256
        or b"declare module 'claude-code'" not in raw
        or b"export type Register =" not in raw
        or b"export type On =" not in raw
        or b"export interface BuiltinToolInputs" not in raw
        or b"$.ui.log(" not in raw
    ):
        raise CliTypesBlocked("Incorrect official reviewed 2.1.302 core declarations")


def _zstd_lib():
    # uv's isolated CPython may not discover the Homebrew location even
    # though the system's official libzstd is present. Restrict fallback
    # loading to known native-library locations; never download or compile
    # an alternate library just to make a QA score pass.
    names = [
        ctypes.util.find_library("zstd"),
        "/opt/homebrew/lib/libzstd.dylib",
        "/usr/local/lib/libzstd.dylib",
        "libzstd.so.1",
    ]
    lib = None
    for name in names:
        if not name:
            continue
        try:
            lib = ctypes.CDLL(name)
            break
        except OSError:
            continue
    if lib is None:
        raise CliTypesBlocked("Native libzstd unavailable, no guessed types allowed")
    lib.ZSTD_findFrameCompressedSize.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    lib.ZSTD_findFrameCompressedSize.restype = ctypes.c_size_t
    lib.ZSTD_getFrameContentSize.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    lib.ZSTD_getFrameContentSize.restype = ctypes.c_ulonglong
    lib.ZSTD_decompress.argtypes = [
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_void_p,
        ctypes.c_size_t,
    ]
    lib.ZSTD_decompress.restype = ctypes.c_size_t
    lib.ZSTD_isError.argtypes = [ctypes.c_size_t]
    lib.ZSTD_isError.restype = ctypes.c_uint
    return lib


def extract_from_binary(binary: Path) -> tuple[bytes, dict]:
    if not binary.is_file() or binary.is_symlink() or binary.stat().st_size < 40_000_000:
        raise CliTypesBlocked("Pinned local Claude 2.1.302 native binary absent")
    binary_digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    if binary_digest not in OFFICIAL_NATIVE_BINARIES:
        raise CliTypesBlocked("Unrecognized target-version binary SHA256")
    lib = _zstd_lib()
    matches: list[tuple[bytes, int, int]] = []
    with binary.open("rb") as source:
        with mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_COPY) as view:
            cur = 0
            frames_considered = 0
            while True:
                cur = view.find(ZSTD_MAGIC, cur)
                if cur < 0:
                    break
                offset = cur
                cur += len(ZSTD_MAGIC)
                frames_considered += 1
                if frames_considered > 12_000:
                    raise CliTypesBlocked("Too many compressed frame candidates")
                frame_ptr = ctypes.addressof(ctypes.c_char.from_buffer(view, offset))
                frame_len = lib.ZSTD_findFrameCompressedSize(frame_ptr, len(view) - offset)
                if lib.ZSTD_isError(frame_len) or not 0 < frame_len <= MAX_FRAME_BYTES:
                    continue
                size = lib.ZSTD_getFrameContentSize(frame_ptr, frame_len)
                if size != DECLARATION_BYTES or size >= MAX_DECLARATION_BYTES:
                    continue
                buffer = ctypes.create_string_buffer(size)
                decompressed = lib.ZSTD_decompress(
                    ctypes.addressof(buffer), size, frame_ptr, frame_len
                )
                if lib.ZSTD_isError(decompressed) or decompressed != size:
                    continue
                raw = buffer.raw
                if digest(raw) == DECLARATION_SHA256:
                    verify_core(raw)
                    matches.append((raw, offset, frame_len))
    if len(matches) != 1:
        raise CliTypesBlocked("Missing or ambiguous exact native CLI 2.1.302 core declarations")
    raw, offset, frame_size = matches[0]
    return raw, {
        "reviewed_cli_version": TARGET_CLI,
        "native_binary_sha256": binary_digest,
        "native_embedded_core_sha256": digest(raw),
        "native_embedded_core_bytes": len(raw),
        "zstd_frame_offset": offset,
        "zstd_frame_bytes": frame_size,
        "source": "embedded official native Claude Code 2.1.302 executable",
        "complete_runtime_generated_tool_declarations_certified": False,
        "model_or_account_calls": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cli-binary",
        type=Path,
        default=Path.home() / ".local/share/claude/versions/2.1.302",
    )
    parser.add_argument("--out-private", type=Path, required=True)
    args = parser.parse_args()
    if args.out_private.exists() or args.out_private.is_symlink():
        raise SystemExit("REFUSED: target private .d.ts already exists")
    if not args.out_private.resolve().is_relative_to(
        Path("/tmp").resolve()  # noqa: S108 - deliberate OS-private temp root
    ):
        raise SystemExit("REFUSED: upstream declaration must stay under private /tmp")
    try:
        raw, meta = extract_from_binary(args.cli_binary)
    except (CliTypesBlocked, OSError, ValueError, ctypes.ArgumentError):
        raise SystemExit("BLOCKED: reviewed CLI302 source/types mismatch") from None
    # The installed engine writes this exact version header on load.
    output = f"// Written by Claude Code {TARGET_CLI}.\n".encode() + raw
    args.out_private.parent.mkdir(parents=True, exist_ok=True)
    with args.out_private.open("xb") as out:
        out.write(output)
    args.out_private.chmod(0o600)
    print(
        {
            "reviewed_version": meta["reviewed_cli_version"],
            "cli302_core_types_sha256": meta["native_embedded_core_sha256"],
            "core_declaration_bytes": meta["native_embedded_core_bytes"],
            "runtime_merged_builtin_tool_types_verified": False,
            "type_file_published_to_git": False,
            "model_requests": 0,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
