"""
Call Duration Tracking - Twilio Status Callbacks

Tracks actual call duration for accurate billing and usage metrics.
Critical for trial enforcement and subscription management.

Features:
- Twilio status callback handler
- Call duration calculation
- Trial usage updates
- Conversation logging integration
- PostgreSQL call records

Author: Claude Code
Date: 2025-11-19
"""

from fastapi import APIRouter, Request, Response, HTTPException
from typing import Dict, Any
import logging
from datetime import datetime

from utils.subscription_manager import get_subscription_manager
from utils.conversation_logger import get_conversation_logger
from utils.logging import log_message

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/twilio/status-callback")
async def handle_call_status(request: Request) -> Response:
    """
    Handle Twilio call status callbacks

    Twilio sends status updates:
    - initiated: Call started
    - ringing: Phone is ringing
    - in-progress: User answered
    - completed: Call ended
    - failed: Call failed
    - busy: User busy
    - no-answer: No answer

    Returns:
        Empty 200 response (Twilio expects this)
    """
    try:
        form = await request.form()

        call_sid = form.get("CallSid")
        call_status = form.get("CallStatus")
        phone_number = form.get("To")  # User's phone number
        duration = form.get("CallDuration")  # Total call duration in seconds

        logger.info(
            f"Call status callback: {call_sid} - Status: {call_status} "
            f"- Duration: {duration}s"
        )

        # Only process completed calls for billing
        if call_status == "completed" and duration:
            await process_completed_call(
                call_sid=call_sid,
                phone_number=phone_number,
                duration_seconds=int(duration),
                form_data=dict(form)
            )

        # Return 200 to acknowledge receipt
        return Response(status_code=200)

    except ValueError as e:
        logger.error(f"Invalid duration value in callback: {e}")
        return Response(status_code=400)
    except Exception as e:
        logger.error(f"Error processing call status callback: {e}", exc_info=True)
        # Still return 200 to prevent Twilio retries
        return Response(status_code=200)


async def process_completed_call(
    call_sid: str,
    phone_number: str,
    duration_seconds: int,
    form_data: Dict[str, Any]
) -> None:
    """
    Process a completed call for billing and logging

    Args:
        call_sid: Twilio call SID
        phone_number: User's phone number
        duration_seconds: Total call duration in seconds
        form_data: Full Twilio callback data
    """
    try:
        duration_minutes = duration_seconds / 60.0

        log_message(
            "info",
            f"[{phone_number}] Call {call_sid} completed - Duration: {duration_minutes:.2f} minutes"
        )

        # Update trial usage if user is on trial
        try:
            sub_mgr = await get_subscription_manager()
            subscription = await sub_mgr.get_subscription(phone_number)

            if subscription and subscription.get("subscription_status") == "trial":
                current_usage = subscription.get("minutes_used_in_trial", 0)
                new_usage = current_usage + duration_minutes

                await sub_mgr.update_trial_usage(phone_number, new_usage)

                log_message(
                    "info",
                    f"[{phone_number}] Trial usage updated: {new_usage:.2f}/{subscription.get('free_trial_minutes', 5)} minutes"
                )

                # Check if trial exhausted
                if new_usage >= subscription.get("free_trial_minutes", 5):
                    log_message(
                        "warning",
                        f"[{phone_number}] Trial exhausted - {new_usage:.2f} minutes used"
                    )

        except Exception as e:
            logger.error(f"Failed to update trial usage: {e}", exc_info=True)

        # Log call completion to PostgreSQL
        try:
            conv_logger = await get_conversation_logger()
            await conv_logger.end_conversation(
                call_sid=call_sid,
                duration_seconds=duration_seconds,
                disconnect_reason=form_data.get("CallStatus", "completed")
            )

            log_message("info", f"[{phone_number}] Call logged to database")

        except Exception as e:
            logger.error(f"Failed to log call to database: {e}", exc_info=True)

        # Track metrics for monitoring
        try:
            await track_call_metrics(
                phone_number=phone_number,
                duration_minutes=duration_minutes,
                call_status="completed"
            )
        except Exception as e:
            logger.error(f"Failed to track call metrics: {e}", exc_info=True)

    except Exception as e:
        logger.error(f"Error processing completed call: {e}", exc_info=True)


async def track_call_metrics(
    phone_number: str,
    duration_minutes: float,
    call_status: str
) -> None:
    """
    Track call metrics for monitoring and alerting

    Args:
        phone_number: User's phone number
        duration_minutes: Call duration in minutes
        call_status: Call status (completed, failed, etc.)
    """
    # In production, send to Datadog/CloudWatch/Prometheus
    # For now, just log

    logger.info(
        f"METRICS: call_completed phone={phone_number} "
        f"duration_minutes={duration_minutes:.2f} status={call_status}"
    )

    # Future: Push to metrics backend
    # await cloudwatch_client.put_metric_data(...)
    # await prometheus_client.gauge("call_duration_minutes").set(duration_minutes)


@router.post("/twilio/recording-callback")
async def handle_recording_status(request: Request) -> Response:
    """
    Handle Twilio recording status callbacks

    Called when call recording is ready for download/processing

    Returns:
        Empty 200 response
    """
    try:
        form = await request.form()

        call_sid = form.get("CallSid")
        recording_sid = form.get("RecordingSid")
        recording_url = form.get("RecordingUrl")
        recording_duration = form.get("RecordingDuration")

        logger.info(
            f"Recording callback: {call_sid} - Recording: {recording_sid} "
            f"- Duration: {recording_duration}s"
        )

        # Store recording URL in database for compliance/training
        try:
            conv_logger = await get_conversation_logger()
            # Future: Add recording_url to conversation record
            logger.info(f"Recording available: {recording_url}")

        except Exception as e:
            logger.error(f"Failed to store recording URL: {e}", exc_info=True)

        return Response(status_code=200)

    except Exception as e:
        logger.error(f"Error processing recording callback: {e}", exc_info=True)
        return Response(status_code=200)
