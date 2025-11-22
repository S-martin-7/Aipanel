"""
Webhook service for managing webhooks and delivering events.
"""
import secrets
import hashlib
import hmac
import json
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.models.webhook import Webhook, WebhookDelivery, WebhookEvent, DeliveryStatus
from app.modules.webhooks.schemas import (
    WebhookCreate, WebhookUpdate, WebhookTestRequest,
    WebhookEventInfo
)


class WebhookService:
    """Service for webhook operations."""

    # Event descriptions for documentation
    EVENT_INFO = {
        WebhookEvent.CONVERSATION_STARTED: ("Conversations", "Triggered when a new conversation starts"),
        WebhookEvent.CONVERSATION_ENDED: ("Conversations", "Triggered when a conversation ends"),
        WebhookEvent.MESSAGE_RECEIVED: ("Messages", "Triggered when a message is received from user"),
        WebhookEvent.MESSAGE_SENT: ("Messages", "Triggered when agent sends a message"),
        WebhookEvent.AGENT_CREATED: ("Agents", "Triggered when a new agent is created"),
        WebhookEvent.AGENT_UPDATED: ("Agents", "Triggered when an agent is updated"),
        WebhookEvent.AGENT_DELETED: ("Agents", "Triggered when an agent is deleted"),
        WebhookEvent.DOCUMENT_UPLOADED: ("Documents", "Triggered when a document is uploaded"),
        WebhookEvent.DOCUMENT_PROCESSED: ("Documents", "Triggered when document processing completes"),
        WebhookEvent.DOCUMENT_DELETED: ("Documents", "Triggered when a document is deleted"),
        WebhookEvent.USER_CREATED: ("Users", "Triggered when a tenant user is created"),
        WebhookEvent.USER_UPDATED: ("Users", "Triggered when a tenant user is updated"),
        WebhookEvent.USER_DELETED: ("Users", "Triggered when a tenant user is deleted"),
        WebhookEvent.SUBSCRIPTION_CREATED: ("Billing", "Triggered when subscription is created"),
        WebhookEvent.SUBSCRIPTION_UPDATED: ("Billing", "Triggered when subscription is updated"),
        WebhookEvent.SUBSCRIPTION_CANCELLED: ("Billing", "Triggered when subscription is cancelled"),
        WebhookEvent.INVOICE_CREATED: ("Billing", "Triggered when an invoice is generated"),
        WebhookEvent.INVOICE_PAID: ("Billing", "Triggered when an invoice is paid"),
    }

    @staticmethod
    def generate_secret() -> str:
        """Generate a webhook signing secret."""
        return secrets.token_hex(32)

    @staticmethod
    def sign_payload(payload: Dict[str, Any], secret: str) -> str:
        """Generate HMAC-SHA256 signature for payload."""
        payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        signature = hmac.new(
            secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"

    async def create_webhook(
        self,
        db: AsyncSession,
        tenant_id: str,
        data: WebhookCreate
    ) -> Webhook:
        """Create a new webhook."""
        webhook = Webhook(
            tenant_id=tenant_id,
            name=data.name,
            url=str(data.url),
            secret=self.generate_secret(),
            events=[e.value for e in data.events],
            agent_id=data.agent_id,
            max_retries=data.max_retries,
            retry_delay_seconds=data.retry_delay_seconds,
            custom_headers=data.custom_headers,
            is_active=data.is_active
        )
        db.add(webhook)
        await db.commit()
        await db.refresh(webhook)
        return webhook

    async def get_webhook(
        self,
        db: AsyncSession,
        webhook_id: str,
        tenant_id: str
    ) -> Optional[Webhook]:
        """Get a webhook by ID."""
        result = await db.execute(
            select(Webhook).where(
                and_(Webhook.id == webhook_id, Webhook.tenant_id == tenant_id)
            )
        )
        return result.scalar_one_or_none()

    async def list_webhooks(
        self,
        db: AsyncSession,
        tenant_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[Webhook], int]:
        """List webhooks for a tenant."""
        # Count
        count_result = await db.execute(
            select(func.count(Webhook.id)).where(Webhook.tenant_id == tenant_id)
        )
        total = count_result.scalar() or 0

        # List
        result = await db.execute(
            select(Webhook)
            .where(Webhook.tenant_id == tenant_id)
            .order_by(Webhook.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        webhooks = list(result.scalars().all())

        return webhooks, total

    async def update_webhook(
        self,
        db: AsyncSession,
        webhook: Webhook,
        data: WebhookUpdate
    ) -> Webhook:
        """Update a webhook."""
        update_data = data.model_dump(exclude_unset=True)

        if 'url' in update_data and update_data['url']:
            update_data['url'] = str(update_data['url'])

        if 'events' in update_data and update_data['events']:
            update_data['events'] = [e.value for e in update_data['events']]

        for field, value in update_data.items():
            setattr(webhook, field, value)

        await db.commit()
        await db.refresh(webhook)
        return webhook

    async def delete_webhook(self, db: AsyncSession, webhook: Webhook) -> None:
        """Delete a webhook."""
        await db.delete(webhook)
        await db.commit()

    async def regenerate_secret(self, db: AsyncSession, webhook: Webhook) -> str:
        """Regenerate webhook secret."""
        new_secret = self.generate_secret()
        webhook.secret = new_secret
        await db.commit()
        return new_secret

    async def test_webhook(
        self,
        webhook: Webhook,
        data: WebhookTestRequest
    ) -> Dict[str, Any]:
        """Test a webhook with a sample payload."""
        event_id = str(uuid4())
        timestamp = datetime.utcnow().isoformat()

        payload = {
            "event": data.event_type.value,
            "event_id": event_id,
            "timestamp": timestamp,
            "test": True,
            "data": data.sample_payload or self._get_sample_payload(data.event_type)
        }

        signature = self.sign_payload(payload, webhook.secret)

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-Event": data.event_type.value,
            "X-Webhook-ID": event_id,
            "User-Agent": "AIPanel-Webhook/1.0"
        }

        if webhook.custom_headers:
            headers.update(webhook.custom_headers)

        start_time = datetime.utcnow()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    webhook.url,
                    json=payload,
                    headers=headers
                )

            response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            return {
                "success": 200 <= response.status_code < 300,
                "status_code": response.status_code,
                "response_time_ms": response_time,
                "response_body": response.text[:1000] if response.text else None,
                "error": None if 200 <= response.status_code < 300 else f"HTTP {response.status_code}"
            }

        except Exception as e:
            return {
                "success": False,
                "status_code": None,
                "response_time_ms": None,
                "response_body": None,
                "error": str(e)
            }

    async def trigger_event(
        self,
        db: AsyncSession,
        tenant_id: str,
        event_type: WebhookEvent,
        data: Dict[str, Any],
        agent_id: Optional[str] = None
    ) -> List[str]:
        """Trigger an event for all matching webhooks."""
        # Find matching webhooks
        query = select(Webhook).where(
            and_(
                Webhook.tenant_id == tenant_id,
                Webhook.is_active == True,
                Webhook.events.contains([event_type.value])
            )
        )

        if agent_id:
            query = query.where(
                (Webhook.agent_id == None) | (Webhook.agent_id == agent_id)
            )

        result = await db.execute(query)
        webhooks = list(result.scalars().all())

        delivery_ids = []

        for webhook in webhooks:
            delivery = await self._create_delivery(db, webhook, event_type, data)
            delivery_ids.append(delivery.id)

            # Queue delivery (in production, use background task queue)
            asyncio.create_task(self._deliver_webhook(db, delivery.id))

        return delivery_ids

    async def _create_delivery(
        self,
        db: AsyncSession,
        webhook: Webhook,
        event_type: WebhookEvent,
        data: Dict[str, Any]
    ) -> WebhookDelivery:
        """Create a webhook delivery record."""
        event_id = str(uuid4())
        timestamp = datetime.utcnow().isoformat()

        payload = {
            "event": event_type.value,
            "event_id": event_id,
            "timestamp": timestamp,
            "data": data
        }

        delivery = WebhookDelivery(
            webhook_id=webhook.id,
            event_type=event_type.value,
            event_id=event_id,
            payload=payload,
            status=DeliveryStatus.PENDING.value
        )
        db.add(delivery)

        webhook.total_deliveries += 1
        webhook.last_triggered_at = datetime.utcnow()

        await db.commit()
        await db.refresh(delivery)
        return delivery

    async def _deliver_webhook(self, db: AsyncSession, delivery_id: str) -> None:
        """Attempt to deliver a webhook."""
        result = await db.execute(
            select(WebhookDelivery).where(WebhookDelivery.id == delivery_id)
        )
        delivery = result.scalar_one_or_none()
        if not delivery:
            return

        webhook_result = await db.execute(
            select(Webhook).where(Webhook.id == delivery.webhook_id)
        )
        webhook = webhook_result.scalar_one_or_none()
        if not webhook:
            return

        signature = self.sign_payload(delivery.payload, webhook.secret)

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-Event": delivery.event_type,
            "X-Webhook-ID": delivery.event_id,
            "X-Webhook-Delivery-ID": delivery.id,
            "User-Agent": "AIPanel-Webhook/1.0"
        }

        if webhook.custom_headers:
            headers.update(webhook.custom_headers)

        delivery.attempts += 1
        start_time = datetime.utcnow()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    webhook.url,
                    json=delivery.payload,
                    headers=headers
                )

            response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            delivery.response_status_code = response.status_code
            delivery.response_body = response.text[:1000] if response.text else None
            delivery.response_time_ms = response_time

            if 200 <= response.status_code < 300:
                delivery.status = DeliveryStatus.SUCCESS.value
                delivery.delivered_at = datetime.utcnow()
                webhook.successful_deliveries += 1
                webhook.last_success_at = datetime.utcnow()
            else:
                await self._handle_failure(
                    db, webhook, delivery,
                    f"HTTP {response.status_code}"
                )

        except Exception as e:
            await self._handle_failure(db, webhook, delivery, str(e))

        await db.commit()

    async def _handle_failure(
        self,
        db: AsyncSession,
        webhook: Webhook,
        delivery: WebhookDelivery,
        error: str
    ) -> None:
        """Handle delivery failure."""
        delivery.error_message = error

        if delivery.attempts < webhook.max_retries:
            delivery.status = DeliveryStatus.RETRYING.value
            delivery.next_retry_at = datetime.utcnow() + timedelta(
                seconds=webhook.retry_delay_seconds * delivery.attempts
            )
        else:
            delivery.status = DeliveryStatus.FAILED.value
            webhook.failed_deliveries += 1
            webhook.last_failure_at = datetime.utcnow()
            webhook.last_failure_reason = error

    async def get_deliveries(
        self,
        db: AsyncSession,
        webhook_id: str,
        tenant_id: str,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[WebhookDelivery], int]:
        """Get deliveries for a webhook."""
        # Verify webhook belongs to tenant
        webhook = await self.get_webhook(db, webhook_id, tenant_id)
        if not webhook:
            return [], 0

        # Build query
        query = select(WebhookDelivery).where(WebhookDelivery.webhook_id == webhook_id)

        if status:
            query = query.where(WebhookDelivery.status == status)

        # Count
        count_query = select(func.count(WebhookDelivery.id)).where(
            WebhookDelivery.webhook_id == webhook_id
        )
        if status:
            count_query = count_query.where(WebhookDelivery.status == status)

        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        # List
        result = await db.execute(
            query.order_by(WebhookDelivery.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        deliveries = list(result.scalars().all())

        return deliveries, total

    async def retry_delivery(
        self,
        db: AsyncSession,
        delivery_id: str,
        tenant_id: str
    ) -> Optional[WebhookDelivery]:
        """Manually retry a failed delivery."""
        result = await db.execute(
            select(WebhookDelivery)
            .join(Webhook)
            .where(
                and_(
                    WebhookDelivery.id == delivery_id,
                    Webhook.tenant_id == tenant_id
                )
            )
        )
        delivery = result.scalar_one_or_none()
        if not delivery:
            return None

        delivery.status = DeliveryStatus.PENDING.value
        delivery.next_retry_at = None
        await db.commit()

        asyncio.create_task(self._deliver_webhook(db, delivery.id))

        return delivery

    async def get_stats(self, db: AsyncSession, tenant_id: str) -> Dict[str, Any]:
        """Get webhook statistics for a tenant."""
        # Webhook counts
        webhooks_result = await db.execute(
            select(
                func.count(Webhook.id).label('total'),
                func.sum(func.cast(Webhook.is_active, Integer)).label('active'),
                func.sum(Webhook.total_deliveries).label('total_deliveries'),
                func.sum(Webhook.successful_deliveries).label('successful'),
                func.sum(Webhook.failed_deliveries).label('failed')
            ).where(Webhook.tenant_id == tenant_id)
        )
        webhook_stats = webhooks_result.first()

        # Deliveries by event type
        by_event_result = await db.execute(
            select(
                WebhookDelivery.event_type,
                func.count(WebhookDelivery.id)
            )
            .join(Webhook)
            .where(Webhook.tenant_id == tenant_id)
            .group_by(WebhookDelivery.event_type)
        )
        by_event = dict(by_event_result.all())

        # Deliveries by status
        by_status_result = await db.execute(
            select(
                WebhookDelivery.status,
                func.count(WebhookDelivery.id)
            )
            .join(Webhook)
            .where(Webhook.tenant_id == tenant_id)
            .group_by(WebhookDelivery.status)
        )
        by_status = dict(by_status_result.all())

        total = webhook_stats.total_deliveries or 0
        successful = webhook_stats.successful or 0

        return {
            "total_webhooks": webhook_stats.total or 0,
            "active_webhooks": webhook_stats.active or 0,
            "total_deliveries": total,
            "successful_deliveries": successful,
            "failed_deliveries": webhook_stats.failed or 0,
            "success_rate": round(successful / total * 100, 2) if total > 0 else 0,
            "deliveries_by_event": by_event,
            "deliveries_by_status": by_status
        }

    def get_available_events(self) -> List[WebhookEventInfo]:
        """Get list of available webhook events."""
        events = []
        for event in WebhookEvent:
            category, description = self.EVENT_INFO.get(
                event, ("Other", "Webhook event")
            )
            events.append(WebhookEventInfo(
                event=event.value,
                category=category,
                description=description,
                sample_payload=self._get_sample_payload(event)
            ))
        return events

    def _get_sample_payload(self, event_type: WebhookEvent) -> Dict[str, Any]:
        """Get sample payload for an event type."""
        samples = {
            WebhookEvent.MESSAGE_RECEIVED: {
                "conversation_id": "conv_123",
                "message_id": "msg_456",
                "content": "Hello, how can I help you?",
                "sender": "user",
                "timestamp": datetime.utcnow().isoformat()
            },
            WebhookEvent.MESSAGE_SENT: {
                "conversation_id": "conv_123",
                "message_id": "msg_789",
                "content": "I can help you with that!",
                "sender": "agent",
                "agent_id": "agent_123",
                "timestamp": datetime.utcnow().isoformat()
            },
            WebhookEvent.AGENT_CREATED: {
                "agent_id": "agent_123",
                "name": "Support Agent",
                "model": "gpt-4",
                "created_by": "user_123"
            },
            WebhookEvent.DOCUMENT_UPLOADED: {
                "document_id": "doc_123",
                "filename": "manual.pdf",
                "size_bytes": 1024000,
                "agent_id": "agent_123"
            },
            WebhookEvent.SUBSCRIPTION_CREATED: {
                "subscription_id": "sub_123",
                "plan": "professional",
                "status": "active",
                "amount": 49900,
                "currency": "CLP"
            }
        }
        return samples.get(event_type, {"example": "data"})


# Singleton instance
webhook_service = WebhookService()


# Convenience function to trigger events from anywhere in the app
async def trigger_webhook_event(
    db: AsyncSession,
    tenant_id: str,
    event_type: WebhookEvent,
    data: Dict[str, Any],
    agent_id: Optional[str] = None
) -> List[str]:
    """Convenience function to trigger webhook events."""
    return await webhook_service.trigger_event(db, tenant_id, event_type, data, agent_id)
