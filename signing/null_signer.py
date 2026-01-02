from __future__ import annotations

from typing import Any, Dict

from .base import SignedTx, Signer


class NullSigner(Signer):
    """
    A safe placeholder signer for paper mode.

    This allows importing/initializing the container without requiring real keys.
    Any attempt to sign will fail closed with a clear error.
    """

    def get_address(self) -> str:
        return "0x0000000000000000000000000000000000000000"

    def sign_transaction(self, tx: Dict[str, Any], *, chain_id: int | None = None) -> SignedTx:  # noqa: ARG002
        raise ValueError("Signer is not configured (paper mode or missing SIGNER_TYPE configuration).")
