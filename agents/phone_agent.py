# Phase 2 — requires Twilio/Vapi integration and IVR training data from Emmanuel
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class PhoneAgent:
    """
    Handles outbound IVR navigation for store ordering lines that do not support
    email or EDI.

    Phase 2 implementation will use Twilio Programmable Voice (or Vapi) to:
      - Dial a store's order department
      - Navigate their IVR tree to reach the purchasing/receiving desk
      - Connect to or leave a message for the manager on duty

    Prerequisites before implementing:
      - Twilio/Vapi credentials in .env (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN,
        TWILIO_FROM_NUMBER or VAPI_API_KEY)
      - IVR decision trees for each store, collected by Emmanuel
      - Call recording consent review with legal
    """

    async def dial_store(self, phone_number: str, store_name: str) -> str:
        """
        Initiate an outbound call to a store's order line.

        Args:
            phone_number: E.164-formatted destination number (e.g. '+16135550123').
            store_name:   Human-readable store name for logging and IVR scripting.

        Returns:
            call_sid: Provider-assigned call identifier for subsequent IVR navigation.
        """
        raise NotImplementedError(
            "PhoneAgent.dial_store() is not implemented — Phase 2 pending Twilio/Vapi setup"
        )

    async def navigate_ivr(self, call_sid: str, target_department: str) -> bool:
        """
        Send DTMF tones or speech commands to navigate an active IVR to the
        target department.

        Args:
            call_sid:          Provider call identifier returned by dial_store().
            target_department: Logical department name (e.g. 'purchasing', 'receiving').
                               Mapped to IVR keypresses via store-specific config.

        Returns:
            True if navigation reached the target department, False if the IVR
            tree was exhausted without reaching it.
        """
        raise NotImplementedError(
            "PhoneAgent.navigate_ivr() is not implemented — Phase 2 pending IVR training data"
        )

    async def connect_to_manager(self, call_sid: str) -> bool:
        """
        After IVR navigation, attempt to reach a human manager or leave a
        structured voicemail if unavailable.

        Args:
            call_sid: Provider call identifier for the active call.

        Returns:
            True if a live human answered, False if call went to voicemail
            (voicemail message is still left and logged).
        """
        raise NotImplementedError(
            "PhoneAgent.connect_to_manager() is not implemented — Phase 2 pending"
        )
