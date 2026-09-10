"""Build the Caspian app. Single entry point for runner, webhooks, and tests.

Two live modes (same handler either way):
- hosted email (default): gateway owns inbound; needs CASPIAN_API_KEY +
  CAMPUSOPS_MAILBOX. `dispatch=False` builds a fully offline app (no
  transport, no gateway I/O) — used by the test suite.
- telegram self-host: our process polls Telegram directly (`cx.poll`);
  needs TELEGRAM_BOT_TOKEN only, no gateway, no public URL.
"""

from __future__ import annotations

from caspian import Caspian

from backend.app.comms.handlers import register


def build_caspian_app(
    *,
    api_key: str = "",
    mailbox: str = "",
    base_url: str = "https://api.trycaspianai.com",
    dispatch: bool = True,
    telegram_bot_token: str = "",
    telegram_via: str = "hosted",
) -> Caspian:
    if telegram_via == "self-host":
        if not telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required for Telegram self-host mode.")
        cx = Caspian(**({} if dispatch else {"dispatch": False}))  # type: ignore[arg-type]
        cx.channels.add("telegram", via="self-host", bot_token=telegram_bot_token)
        return register(cx)
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
    if telegram_bot_token:
        cx.channels.add("telegram", bot_token=telegram_bot_token)
    return register(cx)
