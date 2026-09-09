"""Build the Caspian app. Single entry point for runner, webhooks, and tests.

`dispatch=False` builds a fully offline app (no transport, no gateway I/O) —
used by the test suite. Live processes use the default `dispatch=True`.
"""

from __future__ import annotations

from caspian import Caspian

from backend.app.comms.handlers import register


def build_caspian_app(
    *,
    api_key: str = "",
    mailbox: str,
    base_url: str = "https://api.trycaspianai.com",
    dispatch: bool = True,
) -> Caspian:
    if not mailbox.strip():
        raise ValueError(
            "CAMPUSOPS_MAILBOX is required: pass the agent mailbox local-part "
            "so channels.add() never mints a random address."
        )
    if dispatch and not api_key:
        raise ValueError("CASPIAN_API_KEY is required for a live (dispatch) app.")
    kwargs = {} if dispatch else {"dispatch": False}
    cx = (
        Caspian(api_key=api_key, base_url=base_url, **kwargs)  # type: ignore[arg-type]
        if api_key
        else Caspian(**kwargs)  # type: ignore[arg-type]
    )
    cx.channels.add("email", username=mailbox.strip())
    return register(cx)
