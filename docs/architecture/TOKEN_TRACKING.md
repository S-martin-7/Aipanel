# Sistema de Conteo de Tokens y Uso Justo - AIPanel

Sistema completo para tracking, control y facturación basada en uso de tokens de API de AI.

## [+] Objetivos

1. **Conteo Preciso**: Registrar cada token usado (input, output, reasoning)
2. **Uso Justo**: Establecer límites y umbrales por tenant
3. **Transparencia**: Dashboard en tiempo real del uso
4. **Control de Costos**: Alertas y acciones automáticas
5. **Facturación**: Base para cobro por uso real

## [=] Arquitectura del Sistema

```
┌─────────────────────────────────────────────────┐
│  Cliente hace request → Agente AI               │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  Middleware: Intercepta request                 │
│  - Captura tenant_id                            │
│  - Captura agent_id                             │
│  - Timestamp de inicio                          │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  Call a OpenAI/Anthropic API                    │
│  - Modelo usado                                 │
│  - Parámetros de la request                     │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  Response recibida                               │
│  - usage.prompt_tokens                          │
│  - usage.completion_tokens                      │
│  - usage.total_tokens                           │
│  - (reasoning_tokens si aplica)                 │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  Token Counter Service                          │
│  1. Calcular costo por tipo de token           │
│  2. Guardar en TokenUsage (DB)                  │
│  3. Incrementar tenant.currentMonthUsage        │
│  4. Actualizar Agent.totalInteractions          │
│  5. Verificar umbrales                          │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  Threshold Checker                               │
│  - ¿Excedió 50%? → Alerta info                 │
│  - ¿Excedió 75%? → Alerta warning              │
│  - ¿Excedió 90%? → Alerta critical             │
│  - ¿Excedió 100%? → Throttle o suspend         │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  Actions Triggered                               │
│  - Enviar email de alerta                      │
│  - Crear notificación en dashboard             │
│  - Throttle requests (slow down)               │
│  - Suspender si autoSuspendOnOverage=true      │
└─────────────────────────────────────────────────┘
```

## [?] Modelos de Datos

### Token Usage (Actualizado)

```prisma
model TokenUsage {
  id              String   @id @default(cuid())

  // Identificadores
  tenantId        String
  agentId         String?
  conversationId  String?

  // Request info
  requestId       String   @unique
  endpoint        String   // '/api/agents/chat', '/api/agents/complete'
  model           AIModel

  // Tokens desglosados
  inputTokens     Int      @default(0)
  outputTokens    Int      @default(0)
  reasoningTokens Int      @default(0)  // Solo para O-series
  cachedTokens    Int      @default(0)  // Tokens en caché
  totalTokens     Int      @default(0)

  // Costos desglosados (en USD)
  inputCost       Decimal  @db.Decimal(10, 6)
  outputCost      Decimal  @db.Decimal(10, 6)
  reasoningCost   Decimal  @db.Decimal(10, 6)
  cacheCost       Decimal  @db.Decimal(10, 6)
  totalCost       Decimal  @db.Decimal(10, 6)

  // Metadata de la request
  latencyMs       Int?     // Tiempo de respuesta en ms
  success         Boolean  @default(true)
  errorCode       String?
  errorMessage    String?

  // Timestamp
  timestamp       DateTime @default(now())

  // Relaciones
  tenant          Tenant   @relation(fields: [tenantId], references: [id], onDelete: Cascade)
  agent           Agent?   @relation(fields: [agentId], references: [id], onDelete: SetNull)

  @@index([tenantId, timestamp])
  @@index([agentId, timestamp])
  @@index([requestId])
  @@map("token_usage")
}
```

### Tenant Usage Summary (Agregado por día)

```prisma
model TenantUsageSummary {
  id                String   @id @default(cuid())
  tenantId          String
  date              DateTime // Día específico

  // Agregados del día
  totalRequests     Int      @default(0)
  successfulRequests Int     @default(0)
  failedRequests    Int      @default(0)

  // Tokens totales del día
  totalInputTokens  Int      @default(0)
  totalOutputTokens Int      @default(0)
  totalReasoningTokens Int   @default(0)
  totalTokens       Int      @default(0)

  // Costos totales del día
  totalCost         Decimal  @db.Decimal(10, 2)

  // Por modelo (JSON)
  modelBreakdown    Json     // { "gpt-5-mini": {...}, "claude-sonnet": {...} }

  // Relaciones
  tenant            Tenant   @relation(fields: [tenantId], references: [id], onDelete: Cascade)

  createdAt         DateTime @default(now())
  updatedAt         DateTime @updatedAt

  @@unique([tenantId, date])
  @@index([tenantId, date])
  @@map("tenant_usage_summary")
}
```

### Usage Threshold (Umbrales configurables)

```prisma
model UsageThreshold {
  id              String   @id @default(cuid())
  tenantId        String

  // Tipo de límite
  type            String   // 'daily', 'monthly', 'per_request'

  // Límites en tokens
  maxTokens       Int?
  maxCost         Decimal? @db.Decimal(10, 2)

  // Umbrales de alerta (porcentajes)
  warningAt       Int      @default(75)  // % para warning
  criticalAt      Int      @default(90)  // % para critical

  // Acciones automáticas
  throttleAt      Int?     // % para empezar throttling
  suspendAt       Int?     // % para suspender

  // Throttling config
  throttleDelay   Int?     // ms de delay por request
  throttleMaxRequests Int? // requests máximas por minuto

  // Notificaciones
  notifyEmail     Boolean  @default(true)
  notifyDashboard Boolean  @default(true)
  notifyWebhook   Boolean  @default(false)
  webhookUrl      String?

  // Estado
  isActive        Boolean  @default(true)

  // Relaciones
  tenant          Tenant   @relation(fields: [tenantId], references: [id], onDelete: Cascade)

  createdAt       DateTime @default(now())
  updatedAt       DateTime @updatedAt

  @@index([tenantId])
  @@map("usage_thresholds")
}
```

### Usage Alert (Alertas generadas)

```prisma
model UsageAlert {
  id              String   @id @default(cuid())
  tenantId        String
  thresholdId     String?

  // Tipo de alerta
  level           String   // 'info', 'warning', 'critical'
  type            String   // 'threshold_exceeded', 'daily_limit', 'monthly_limit'

  // Mensaje
  title           String
  message         String   @db.Text

  // Datos del uso
  currentUsage    Int      // Tokens usados
  limit           Int      // Límite configurado
  percentage      Int      // % del límite alcanzado

  // Metadata
  metadata        Json?

  // Estado
  isRead          Boolean  @default(false)
  isResolved      Boolean  @default(false)
  resolvedAt      DateTime?

  // Acciones tomadas
  actionTaken     String?  // 'email_sent', 'throttled', 'suspended'

  // Relaciones
  tenant          Tenant   @relation(fields: [tenantId], references: [id], onDelete: Cascade)

  createdAt       DateTime @default(now())

  @@index([tenantId, isResolved])
  @@index([createdAt])
  @@map("usage_alerts")
}
```

## [?] Cálculo de Costos por Modelo

```python
# backend/app/services/token_pricing.py
from decimal import Decimal
from app.models.enums import AIModel

# Precios por 1K tokens (actualizar según API)
MODEL_PRICING = {
    AIModel.GPT5_MINI: {
        "input": Decimal("0.010"),      # $0.010 por 1K tokens input
        "output": Decimal("0.020"),     # $0.020 por 1K tokens output
        "reasoning": Decimal("0.040"),  # $0.040 por 1K reasoning tokens
        "cached": Decimal("0.001"),     # $0.001 por 1K cached tokens
    },
    AIModel.GPT_REALTIME_MINI: {
        "input": Decimal("0.032"),      # Audio input
        "output": Decimal("0.032"),     # Audio output
        "cached": Decimal("0.0004"),    # Cached audio
    },
    AIModel.CLAUDE_SONNET_4_5: {
        "input": Decimal("0.003"),
        "output": Decimal("0.015"),
        "cached": Decimal("0.0003"),
    },
    # ... más modelos
}

def calculate_cost(
    model: AIModel,
    input_tokens: int,
    output_tokens: int,
    reasoning_tokens: int = 0,
    cached_tokens: int = 0
) -> dict:
    """
    Calcula el costo de una request de AI.

    Returns:
        {
            "input_cost": Decimal,
            "output_cost": Decimal,
            "reasoning_cost": Decimal,
            "cache_cost": Decimal,
            "total_cost": Decimal
        }
    """
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        raise ValueError(f"Pricing not found for model: {model}")

    # Calcular costos (dividir por 1000 porque el precio es por 1K tokens)
    input_cost = (Decimal(input_tokens) / 1000) * pricing["input"]
    output_cost = (Decimal(output_tokens) / 1000) * pricing["output"]
    reasoning_cost = (Decimal(reasoning_tokens) / 1000) * pricing.get("reasoning", Decimal(0))
    cache_cost = (Decimal(cached_tokens) / 1000) * pricing.get("cached", Decimal(0))

    total_cost = input_cost + output_cost + reasoning_cost + cache_cost

    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "reasoning_cost": reasoning_cost,
        "cache_cost": cache_cost,
        "total_cost": total_cost
    }
```

## [?] Servicio de Tracking de Tokens

```python
# backend/app/services/token_tracker.py
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import TokenUsage, Tenant, Agent
from app.services.token_pricing import calculate_cost
from app.services.threshold_checker import check_thresholds
import uuid

class TokenTracker:
    """Servicio para registrar y trackear uso de tokens"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def track_usage(
        self,
        tenant_id: str,
        agent_id: str | None,
        model: str,
        input_tokens: int,
        output_tokens: int,
        reasoning_tokens: int = 0,
        cached_tokens: int = 0,
        endpoint: str = "/api/agents/chat",
        conversation_id: str | None = None,
        latency_ms: int | None = None,
        success: bool = True,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> TokenUsage:
        """
        Registra el uso de tokens de una request.

        Args:
            tenant_id: ID del tenant
            agent_id: ID del agente (opcional)
            model: Modelo de AI usado
            input_tokens: Tokens de input
            output_tokens: Tokens de output
            reasoning_tokens: Tokens de razonamiento (O-series)
            cached_tokens: Tokens cacheados
            endpoint: Endpoint llamado
            conversation_id: ID de conversación
            latency_ms: Latencia de la request
            success: Si fue exitosa
            error_code: Código de error si falló
            error_message: Mensaje de error

        Returns:
            TokenUsage object creado
        """

        # Calcular totales
        total_tokens = input_tokens + output_tokens + reasoning_tokens

        # Calcular costos
        costs = calculate_cost(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=reasoning_tokens,
            cached_tokens=cached_tokens
        )

        # Crear registro de uso
        usage = TokenUsage(
            request_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            agent_id=agent_id,
            conversation_id=conversation_id,
            endpoint=endpoint,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=reasoning_tokens,
            cached_tokens=cached_tokens,
            total_tokens=total_tokens,
            input_cost=costs["input_cost"],
            output_cost=costs["output_cost"],
            reasoning_cost=costs["reasoning_cost"],
            cache_cost=costs["cache_cost"],
            total_cost=costs["total_cost"],
            latency_ms=latency_ms,
            success=success,
            error_code=error_code,
            error_message=error_message,
            timestamp=datetime.utcnow()
        )

        self.db.add(usage)

        # Actualizar contador del tenant
        tenant = await self.db.get(Tenant, tenant_id)
        if tenant:
            tenant.current_month_usage += total_tokens

        # Actualizar estadísticas del agente
        if agent_id:
            agent = await self.db.get(Agent, agent_id)
            if agent:
                agent.total_interactions += 1
                agent.total_cost += costs["total_cost"]

        await self.db.commit()
        await self.db.refresh(usage)

        # Verificar umbrales (async task)
        await check_thresholds(self.db, tenant_id)

        return usage

    async def get_tenant_usage_today(self, tenant_id: str) -> dict:
        """Obtiene el uso del tenant en el día actual"""
        from sqlalchemy import func, select
        from datetime import date

        today = date.today()

        result = await self.db.execute(
            select(
                func.count(TokenUsage.id).label("total_requests"),
                func.sum(TokenUsage.total_tokens).label("total_tokens"),
                func.sum(TokenUsage.total_cost).label("total_cost")
            )
            .where(
                TokenUsage.tenant_id == tenant_id,
                func.date(TokenUsage.timestamp) == today,
                TokenUsage.success == True
            )
        )

        row = result.first()

        return {
            "total_requests": row.total_requests or 0,
            "total_tokens": int(row.total_tokens or 0),
            "total_cost": float(row.total_cost or 0)
        }
```

## [!] Sistema de Umbrales y Alertas

```python
# backend/app/services/threshold_checker.py
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Tenant, UsageThreshold, UsageAlert
from app.tasks.notifications import send_usage_alert_email

async def check_thresholds(db: AsyncSession, tenant_id: str):
    """
    Verifica si el tenant ha excedido algún umbral y toma acciones.
    """
    # Obtener tenant
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        return

    # Obtener umbrales activos
    thresholds = await db.execute(
        select(UsageThreshold)
        .where(
            UsageThreshold.tenant_id == tenant_id,
            UsageThreshold.is_active == True
        )
    )
    thresholds = thresholds.scalars().all()

    for threshold in thresholds:
        if threshold.type == "monthly":
            await _check_monthly_threshold(db, tenant, threshold)
        elif threshold.type == "daily":
            await _check_daily_threshold(db, tenant, threshold)

async def _check_monthly_threshold(
    db: AsyncSession,
    tenant: Tenant,
    threshold: UsageThreshold
):
    """Verifica umbral mensual"""

    current_usage = tenant.current_month_usage
    limit = threshold.max_tokens or tenant.monthly_token_limit

    if limit == 0:
        return

    percentage = int((current_usage / limit) * 100)

    # Verificar niveles de alerta
    if percentage >= 100 and threshold.suspend_at:
        # SUSPENDER TENANT
        if tenant.auto_suspend_on_overage:
            tenant.status = "SUSPENDED"
            await db.commit()

            await _create_alert(
                db,
                tenant_id=tenant.id,
                threshold_id=threshold.id,
                level="critical",
                type="monthly_limit_exceeded",
                title="Límite mensual excedido - Cuenta suspendida",
                message=f"Has excedido tu límite mensual de {limit:,} tokens. Tu cuenta ha sido suspendida.",
                current_usage=current_usage,
                limit=limit,
                percentage=percentage,
                action_taken="suspended"
            )

            if threshold.notify_email:
                await send_usage_alert_email.delay(tenant.id, "suspended")

    elif percentage >= threshold.critical_at:
        # ALERTA CRÍTICA
        await _create_alert(
            db,
            tenant_id=tenant.id,
            threshold_id=threshold.id,
            level="critical",
            type="threshold_exceeded",
            title=f"Uso crítico: {percentage}% del límite mensual",
            message=f"Has usado {current_usage:,} de {limit:,} tokens ({percentage}%). La cuenta será suspendida al llegar al 100%.",
            current_usage=current_usage,
            limit=limit,
            percentage=percentage
        )

        if threshold.notify_email:
            await send_usage_alert_email.delay(tenant.id, "critical")

    elif percentage >= threshold.warning_at:
        # ALERTA WARNING
        await _create_alert(
            db,
            tenant_id=tenant.id,
            threshold_id=threshold.id,
            level="warning",
            type="threshold_exceeded",
            title=f"Advertencia: {percentage}% del límite mensual",
            message=f"Has usado {current_usage:,} de {limit:,} tokens ({percentage}%).",
            current_usage=current_usage,
            limit=limit,
            percentage=percentage
        )

        if threshold.notify_email:
            await send_usage_alert_email.delay(tenant.id, "warning")

async def _create_alert(
    db: AsyncSession,
    tenant_id: str,
    threshold_id: str | None,
    level: str,
    type: str,
    title: str,
    message: str,
    current_usage: int,
    limit: int,
    percentage: int,
    action_taken: str | None = None
):
    """Crea una alerta de uso"""

    # Verificar si ya existe una alerta similar sin resolver
    existing = await db.execute(
        select(UsageAlert)
        .where(
            UsageAlert.tenant_id == tenant_id,
            UsageAlert.type == type,
            UsageAlert.is_resolved == False
        )
    )
    existing_alert = existing.scalar_one_or_none()

    if existing_alert:
        # Actualizar alerta existente
        existing_alert.level = level
        existing_alert.message = message
        existing_alert.current_usage = current_usage
        existing_alert.percentage = percentage
        existing_alert.action_taken = action_taken
    else:
        # Crear nueva alerta
        alert = UsageAlert(
            tenant_id=tenant_id,
            threshold_id=threshold_id,
            level=level,
            type=type,
            title=title,
            message=message,
            current_usage=current_usage,
            limit=limit,
            percentage=percentage,
            action_taken=action_taken
        )
        db.add(alert)

    await db.commit()
```

## [^] Dashboard de Métricas

```python
# backend/app/api/v1/usage.py
from fastapi import APIRouter, Depends
from app.api.deps import get_current_tenant_user
from app.services.token_tracker import TokenTracker

router = APIRouter()

@router.get("/usage/summary")
async def get_usage_summary(
    current_user = Depends(get_current_tenant_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene resumen de uso para el tenant.

    Returns:
        {
            "current_month": {
                "tokens_used": 150000,
                "tokens_limit": 500000,
                "percentage": 30,
                "total_cost": 45.50,
                "requests": 1234
            },
            "today": {
                "tokens_used": 5000,
                "total_cost": 1.25,
                "requests": 45
            },
            "by_model": {
                "gpt-5-mini": { "tokens": 100000, "cost": 30.00 },
                "claude-sonnet": { "tokens": 50000, "cost": 15.50 }
            },
            "alerts": [...]
        }
    """
    tracker = TokenTracker(db)
    tenant = current_user.tenant

    # Uso del mes actual
    month_summary = {
        "tokens_used": tenant.current_month_usage,
        "tokens_limit": tenant.monthly_token_limit,
        "percentage": int((tenant.current_month_usage / tenant.monthly_token_limit) * 100),
        "status": "ok" if tenant.status == "ACTIVE" else "suspended"
    }

    # Uso de hoy
    today_usage = await tracker.get_tenant_usage_today(tenant.id)

    # Por modelo (últimos 30 días)
    model_breakdown = await _get_usage_by_model(db, tenant.id, days=30)

    # Alertas no leídas
    alerts = await _get_unread_alerts(db, tenant.id)

    return {
        "current_month": month_summary,
        "today": today_usage,
        "by_model": model_breakdown,
        "alerts": alerts
    }
```

## [+] Umbrales Recomendados

```python
# Configuración por defecto para nuevos tenants
DEFAULT_THRESHOLDS = {
    "monthly": {
        "type": "monthly",
        "max_tokens": None,  # Se usa tenant.monthly_token_limit
        "warning_at": 75,    # Alerta al 75%
        "critical_at": 90,   # Alerta crítica al 90%
        "suspend_at": 100,   # Suspender al 100%
        "notify_email": True,
        "notify_dashboard": True
    },
    "daily": {
        "type": "daily",
        "max_tokens": lambda monthly: monthly // 30,  # ~3.3% del mensual
        "warning_at": 80,
        "critical_at": 95,
        "throttle_at": 90,   # Empezar throttling al 90%
        "throttle_delay": 1000,  # 1 segundo de delay
        "notify_email": True
    }
}
```

## [=] Reportes y Análisis

```python
@router.get("/usage/history")
async def get_usage_history(
    days: int = 30,
    current_user = Depends(get_current_tenant_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene historial de uso.

    Returns:
        [
            {
                "date": "2025-01-15",
                "tokens": 15000,
                "cost": 4.50,
                "requests": 123
            },
            ...
        ]
    """
    # Consultar TenantUsageSummary por fecha
    ...
```

---

**Sistema completo de conteo y control de tokens implementado con:**
- [OK] Tracking preciso por request
- [OK] Costos calculados automáticamente
- [OK] Umbrales configurables
- [OK] Alertas automáticas multinivel
- [OK] Suspensión automática opcional
- [OK] Dashboard en tiempo real
- [OK] Historial completo
- [OK] Base para facturación por uso
