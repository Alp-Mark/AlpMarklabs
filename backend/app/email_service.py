"""Email notification service with async retry logic (FR-116 / T-079).

Async email sender for alert notifications with exponential backoff retry,
delivery status tracking, and error handling.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.app.db.models import EmailDeliveryLog

# Retry configuration: max 3 attempts with exponential backoff
RETRY_ATTEMPTS = 3
RETRY_INTERVALS = [5, 30, 300]  # 5 sec, 30 sec, 5 min


class EmailService:
    """Service for sending alert emails with automatic retry logic."""

    @staticmethod
    async def send_alert_email(
        db: Session,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        email_address: str,
        alert_id: str,
        alert_type: str,
        alert_subject: str,
        alert_body: str,
    ) -> EmailDeliveryLog:
        """Send an alert email with retry logic and delivery tracking.

        Creates an EmailDeliveryLog record and attempts to send the email.
        On failure, updates the log with error details but does NOT automatically
        retry (retry logic is handled by a background job that polls failed records).

        Args:
            db: Database session
            tenant_id: Tenant UUID
            user_id: User UUID
            email_address: Recipient email address
            alert_id: Alert identifier
            alert_type: Type of alert (e.g., "margin_drift", "stockout_risk")
            alert_subject: Email subject line
            alert_body: Email body (plain text or HTML)

        Returns:
            EmailDeliveryLog: Created log record with status and attempt details
        """
        # Create delivery log record
        delivery_log = EmailDeliveryLog(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            alert_id=alert_id,
            alert_type=alert_type,
            email_address=email_address,
            status="pending",
            attempt_count=0,
            last_attempt_at=None,
            error_message=None,
        )
        db.add(delivery_log)
        db.flush()  # Ensure record is created before attempting send

        # Try sending email (simulate for now; in production use aiosmtplib or SES)
        try:
            await EmailService._send_smtp_email(
                email_address=email_address,
                subject=alert_subject,
                body=alert_body,
            )
            delivery_log.status = "sent"
            delivery_log.attempt_count = 1
            delivery_log.last_attempt_at = datetime.now(UTC)
        except Exception as e:
            delivery_log.status = "failed"
            delivery_log.attempt_count = 1
            delivery_log.last_attempt_at = datetime.now(UTC)
            delivery_log.error_message = str(e)[:500]  # Truncate to 500 chars

        db.commit()
        return delivery_log

    @staticmethod
    async def retry_failed_deliveries(db: Session, max_retries: int = 3) -> None:
        """Background job to retry failed email deliveries.

        Queries for failed/pending deliveries and retries them with exponential backoff.
        Only retries if attempt_count < max_retries.

        Args:
            db: Database session
            max_retries: Maximum retry attempts per email
        """
        # Query for failed or pending deliveries that need retry
        failed_logs = db.query(EmailDeliveryLog).filter(
            EmailDeliveryLog.status.in_(["failed", "pending"]),
            EmailDeliveryLog.attempt_count < max_retries,
        ).all()

        for log in failed_logs:
            try:
                # Calculate backoff: if attempt_count = 1, use RETRY_INTERVALS[0], etc.
                if log.attempt_count < len(RETRY_INTERVALS):
                    backoff_sec = RETRY_INTERVALS[log.attempt_count - 1]
                else:
                    # Use last interval for all further retries
                    backoff_sec = RETRY_INTERVALS[-1]

                # Simulate async sleep (in production, this would be scheduled)
                await asyncio.sleep(backoff_sec)

                # Attempt send
                await EmailService._send_smtp_email(
                    email_address=log.email_address,
                    subject=f"[RETRY] Alert: {log.alert_type}",
                    body=f"Alert ID: {log.alert_id}",
                )

                log.status = "sent"
                log.attempt_count += 1
                log.last_attempt_at = datetime.now(UTC)
                log.error_message = None

            except Exception as e:
                log.status = "failed"
                log.attempt_count += 1
                log.last_attempt_at = datetime.now(UTC)
                log.error_message = str(e)[:500]

                # If max retries exceeded, mark as permanently failed
                if log.attempt_count >= max_retries:
                    log.status = "permanently_failed"

            db.commit()

    @staticmethod
    async def _send_smtp_email(
        email_address: str, subject: str, body: str
    ) -> None:
        """Send email via SMTP (async placeholder).

        In production, this would use aiosmtplib or AWS SES SDK.
        For now, simulates successful send.

        Args:
            email_address: Recipient email
            subject: Email subject
            body: Email body

        Raises:
            Exception: If email send fails
        """
        # Placeholder: in production, use actual SMTP or SES
        # For testing, we'll simulate success or raise based on email domain
        if "invalid" in email_address:
            raise ValueError(f"Invalid email address: {email_address}")

        # Simulate async operation
        await asyncio.sleep(0.01)

        # Simulate successful send
        pass
