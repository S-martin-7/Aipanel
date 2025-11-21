# Sistema de Control de Ingresos por Tenant

## Resumen Ejecutivo

AIPanel incluye un sistema completo de control de ingresos que permite monitorear, analizar y proyectar los ingresos generados por cada tenant. Este sistema es fundamental para:

- Tracking de MRR (Monthly Recurring Revenue)
- Análisis de churn y retención
- Identificación de tenants más rentables
- Detección de oportunidades de upselling
- Proyecciones financieras
- Reportes ejecutivos y operacionales

## Objetivos del Sistema

1. **Visibilidad Total**: Ver ingresos en tiempo real por tenant, plan, período
2. **Desglose Detallado**: Separar ingresos base, overages, add-ons, servicios
3. **Análisis Temporal**: Comparar períodos, identificar tendencias
4. **Alertas Proactivas**: Notificar sobre cancelaciones, downgrades, oportunidades
5. **Reportes Automáticos**: Generar reportes ejecutivos mensuales/trimestrales
6. **Integración Contable**: Exportar datos para sistemas contables (SII Chile)

---

## Arquitectura del Sistema

### Componentes Principales

```
┌─────────────────────────────────────────┐
│     Frontend Dashboard de Ingresos      │
│  - Vista ejecutiva (KPIs generales)     │
│  - Vista por tenant (detalle)           │
│  - Reportes y gráficos                  │
└─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│       Backend API de Billing            │
│  - Tracking de pagos                    │
│  - Cálculo de overages                  │
│  - Generación de facturas               │
│  - Reportes de ingresos                 │
└─────────────────────────────────────────┘
                  │
        ┌─────────┼─────────┐
        ▼         ▼         ▼
  ┌──────────┐ ┌──────┐ ┌──────────┐
  │PostgreSQL│ │Redis │ │Transbank │
  │ (billing)│ │(cache)│ │  (pagos) │
  └──────────┘ └──────┘ └──────────┘
```

---

## Schema de Base de Datos

### Tabla: subscriptions

Gestión de suscripciones por tenant:

```sql
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Plan y estado
    plan VARCHAR(50) NOT NULL,  -- 'basico', 'pro', 'enterprise'
    status VARCHAR(50) NOT NULL,  -- 'active', 'trialing', 'past_due', 'canceled', 'suspended'

    -- Precios (en CLP)
    base_price INTEGER NOT NULL,  -- Precio base mensual
    currency VARCHAR(3) DEFAULT 'CLP',

    -- Cuotas incluidas en el plan
    included_memory_gb DECIMAL(10,2) NOT NULL,
    included_tokens INTEGER NOT NULL,
    included_agents INTEGER NOT NULL,
    included_users INTEGER NOT NULL,

    -- Ciclo de facturación
    billing_cycle VARCHAR(20) DEFAULT 'monthly',  -- 'monthly', 'yearly'
    billing_period_start DATE NOT NULL,
    billing_period_end DATE NOT NULL,
    next_billing_date DATE NOT NULL,

    -- Trial
    trial_start TIMESTAMPTZ,
    trial_end TIMESTAMPTZ,

    -- Cancelación
    canceled_at TIMESTAMPTZ,
    cancellation_reason TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

CREATE INDEX idx_subscriptions_tenant_id ON subscriptions(tenant_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_next_billing_date ON subscriptions(next_billing_date);
```

### Tabla: invoices

Facturas generadas por el sistema:

```sql
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    subscription_id UUID REFERENCES subscriptions(id),

    -- Identificación
    invoice_number VARCHAR(50) UNIQUE NOT NULL,  -- Ej: "INV-2025-01-0001"

    -- Estado
    status VARCHAR(50) NOT NULL,  -- 'draft', 'pending', 'paid', 'failed', 'refunded'

    -- Montos (en CLP)
    subtotal INTEGER NOT NULL,
    tax INTEGER DEFAULT 0,  -- IVA 19%
    total INTEGER NOT NULL,
    amount_paid INTEGER DEFAULT 0,
    amount_due INTEGER NOT NULL,

    -- Período facturado
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,

    -- Fechas importantes
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    paid_at TIMESTAMPTZ,

    -- Integración con Transbank
    transbank_token VARCHAR(255),
    transbank_order_id VARCHAR(100),

    -- Facturación electrónica SII
    sii_folio INTEGER,  -- Folio de factura electrónica
    sii_pdf_url TEXT,   -- URL del PDF de la factura
    sii_xml_url TEXT,   -- URL del XML de la factura

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

CREATE INDEX idx_invoices_tenant_id ON invoices(tenant_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_issue_date ON invoices(issue_date);
CREATE INDEX idx_invoices_due_date ON invoices(due_date);
CREATE UNIQUE INDEX idx_invoices_number ON invoices(invoice_number);
```

### Tabla: invoice_line_items

Líneas de detalle de cada factura:

```sql
CREATE TABLE invoice_line_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,

    -- Descripción del item
    description TEXT NOT NULL,
    item_type VARCHAR(50) NOT NULL,  -- 'base_plan', 'memory_overage', 'token_overage', 'addon', 'service'

    -- Cantidades
    quantity DECIMAL(10,2) DEFAULT 1,
    unit_price INTEGER NOT NULL,

    -- Monto
    amount INTEGER NOT NULL,

    -- Metadata para referencias
    metadata JSONB,  -- Ej: {"agent_id": "...", "period": "2025-01"}

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_line_items_invoice_id ON invoice_line_items(invoice_id);
CREATE INDEX idx_line_items_type ON invoice_line_items(item_type);
```

### Tabla: payments

Registro de pagos recibidos:

```sql
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    invoice_id UUID REFERENCES invoices(id),

    -- Monto
    amount INTEGER NOT NULL,
    currency VARCHAR(3) DEFAULT 'CLP',

    -- Estado
    status VARCHAR(50) NOT NULL,  -- 'pending', 'completed', 'failed', 'refunded'

    -- Método de pago
    payment_method VARCHAR(50),  -- 'transbank_webpay', 'transfer', 'khipu'

    -- Transbank
    transbank_transaction_id VARCHAR(255),
    transbank_authorization_code VARCHAR(100),
    transbank_card_type VARCHAR(50),  -- 'credit', 'debit'
    transbank_card_last4 VARCHAR(4),

    -- Comprobante
    receipt_url TEXT,

    -- Timestamps
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
    CONSTRAINT fk_invoice FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);

CREATE INDEX idx_payments_tenant_id ON payments(tenant_id);
CREATE INDEX idx_payments_invoice_id ON payments(invoice_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_paid_at ON payments(paid_at);
```

### Tabla: revenue_events

Eventos de ingresos para analytics:

```sql
CREATE TABLE revenue_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),

    -- Tipo de evento
    event_type VARCHAR(50) NOT NULL,  -- 'subscription_started', 'subscription_upgraded', 'subscription_downgraded', 'subscription_canceled', 'payment_received', 'overage_charged', 'addon_purchased'

    -- Montos
    amount INTEGER NOT NULL,
    mrr_change INTEGER DEFAULT 0,  -- Cambio en MRR (Monthly Recurring Revenue)

    -- Metadata
    description TEXT,
    metadata JSONB,

    -- Timestamp
    occurred_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

CREATE INDEX idx_revenue_events_tenant_id ON revenue_events(tenant_id);
CREATE INDEX idx_revenue_events_type ON revenue_events(event_type);
CREATE INDEX idx_revenue_events_occurred_at ON revenue_events(occurred_at);
```

---

## API Endpoints

### Gestión de Suscripciones

#### POST /api/v1/billing/subscriptions
Crear suscripción para un tenant:

```json
{
  "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
  "plan": "pro",
  "billing_cycle": "monthly",
  "trial_days": 14
}
```

#### GET /api/v1/billing/subscriptions/:tenant_id
Obtener suscripción actual de un tenant:

```json
{
  "id": "sub_123",
  "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
  "plan": "pro",
  "status": "active",
  "base_price": 49990,
  "billing_period_start": "2025-01-01",
  "billing_period_end": "2025-01-31",
  "next_billing_date": "2025-02-01",
  "usage": {
    "memory_gb": 3.5,
    "tokens": 1200000,
    "agents": 7,
    "users": 18
  },
  "limits": {
    "memory_gb": 5,
    "tokens": 1500000,
    "agents": 10,
    "users": 25
  }
}
```

#### PATCH /api/v1/billing/subscriptions/:id
Actualizar suscripción (upgrade/downgrade):

```json
{
  "plan": "enterprise",
  "prorate": true
}
```

### Gestión de Facturas

#### GET /api/v1/billing/invoices
Listar facturas con filtros:

```
GET /api/v1/billing/invoices?tenant_id=xxx&status=paid&from=2025-01-01&to=2025-01-31
```

Response:
```json
{
  "invoices": [
    {
      "id": "inv_123",
      "invoice_number": "INV-2025-01-0001",
      "tenant_id": "...",
      "tenant_name": "Empresa ABC",
      "status": "paid",
      "total": 49990,
      "period_start": "2025-01-01",
      "period_end": "2025-01-31",
      "issue_date": "2025-01-31",
      "paid_at": "2025-02-01T10:30:00Z",
      "line_items": [
        {
          "description": "Plan Pro - Enero 2025",
          "item_type": "base_plan",
          "amount": 49990
        }
      ]
    }
  ],
  "total_count": 150,
  "page": 1,
  "per_page": 20
}
```

#### GET /api/v1/billing/invoices/:id
Detalle completo de una factura:

```json
{
  "id": "inv_123",
  "invoice_number": "INV-2025-01-0001",
  "tenant": {
    "id": "...",
    "name": "Empresa ABC",
    "email": "contacto@empresaabc.cl",
    "rut": "76.123.456-7"
  },
  "status": "paid",
  "subtotal": 41975,
  "tax": 7975,  // IVA 19%
  "total": 49990,
  "amount_paid": 49990,
  "amount_due": 0,
  "period_start": "2025-01-01",
  "period_end": "2025-01-31",
  "issue_date": "2025-01-31",
  "due_date": "2025-02-15",
  "paid_at": "2025-02-01T10:30:00Z",
  "line_items": [
    {
      "description": "Plan Pro - Enero 2025",
      "item_type": "base_plan",
      "quantity": 1,
      "unit_price": 49990,
      "amount": 49990
    }
  ],
  "payment": {
    "method": "transbank_webpay",
    "transaction_id": "TBK_123456789",
    "card_type": "credit",
    "card_last4": "4567"
  },
  "sii": {
    "folio": 12345,
    "pdf_url": "https://...",
    "xml_url": "https://..."
  }
}
```

#### POST /api/v1/billing/invoices/:id/send
Enviar factura por email al tenant.

#### GET /api/v1/billing/invoices/:id/pdf
Descargar PDF de la factura.

### Reportes de Ingresos

#### GET /api/v1/billing/revenue/summary
Resumen de ingresos con KPIs principales:

```json
{
  "period": {
    "from": "2025-01-01",
    "to": "2025-01-31"
  },
  "metrics": {
    "mrr": 8500000,  // Monthly Recurring Revenue
    "arr": 102000000,  // Annual Recurring Revenue
    "total_revenue": 9200000,  // MRR + overages + add-ons
    "base_revenue": 8500000,
    "overage_revenue": 450000,
    "addon_revenue": 250000,
    "active_subscriptions": 175,
    "new_subscriptions": 12,
    "canceled_subscriptions": 3,
    "churn_rate": 1.7,  // %
    "average_revenue_per_tenant": 48571,
    "ltv": 583000  // Lifetime Value promedio
  },
  "by_plan": {
    "basico": {
      "count": 100,
      "mrr": 1999000
    },
    "pro": {
      "count": 60,
      "mrr": 2999400
    },
    "enterprise": {
      "count": 15,
      "mrr": 3500000
    }
  },
  "growth": {
    "mrr_growth": 12.5,  // % vs mes anterior
    "arr_growth": 15.2
  }
}
```

#### GET /api/v1/billing/revenue/by-tenant
Ingresos desglosados por tenant:

```json
{
  "tenants": [
    {
      "tenant_id": "...",
      "tenant_name": "Empresa ABC",
      "plan": "enterprise",
      "status": "active",
      "mrr": 199000,
      "total_revenue_current_month": 215000,
      "total_revenue_last_month": 199000,
      "growth": 8.0,  // %
      "base_revenue": 199000,
      "overage_revenue": 16000,
      "breakdown": {
        "base_plan": 199000,
        "memory_overage": 12000,
        "token_overage": 4000,
        "addons": 0
      },
      "usage": {
        "memory_gb": 22.5,
        "tokens": 11200000,
        "agents": 15
      },
      "subscription_start": "2024-06-01",
      "lifetime_value": 1593000,
      "payment_status": "current"
    },
    // ... más tenants
  ],
  "total_count": 175,
  "page": 1,
  "per_page": 20
}
```

#### GET /api/v1/billing/revenue/timeline
Serie temporal de ingresos:

```
GET /api/v1/billing/revenue/timeline?from=2024-01-01&to=2025-01-31&granularity=month
```

Response:
```json
{
  "timeline": [
    {
      "period": "2024-01",
      "mrr": 6500000,
      "total_revenue": 6800000,
      "active_subscriptions": 120,
      "new_subscriptions": 15,
      "canceled_subscriptions": 2
    },
    {
      "period": "2024-02",
      "mrr": 7200000,
      "total_revenue": 7600000,
      "active_subscriptions": 133,
      "new_subscriptions": 18,
      "canceled_subscriptions": 5
    },
    // ... más períodos
  ]
}
```

#### GET /api/v1/billing/revenue/forecast
Proyección de ingresos:

```json
{
  "current_mrr": 8500000,
  "forecast": [
    {
      "month": "2025-02",
      "projected_mrr": 8900000,
      "confidence": "high"
    },
    {
      "month": "2025-03",
      "projected_mrr": 9400000,
      "confidence": "medium"
    },
    {
      "month": "2025-04",
      "projected_mrr": 9800000,
      "confidence": "medium"
    }
  ],
  "assumptions": {
    "monthly_growth_rate": 5.0,  // %
    "churn_rate": 2.0  // %
  }
}
```

#### GET /api/v1/billing/revenue/cohorts
Análisis de cohortes de tenants:

```json
{
  "cohorts": [
    {
      "cohort": "2024-01",
      "initial_size": 45,
      "current_size": 38,
      "retention_rate": 84.4,
      "mrr_start": 1200000,
      "mrr_current": 1850000,
      "lifetime_months": 13,
      "avg_ltv": 520000
    },
    // ... más cohortes
  ]
}
```

### Alertas y Notificaciones

#### GET /api/v1/billing/alerts
Alertas de ingresos pendientes:

```json
{
  "alerts": [
    {
      "type": "payment_failed",
      "severity": "high",
      "tenant_id": "...",
      "tenant_name": "Empresa XYZ",
      "message": "Pago fallido por 3ra vez",
      "amount": 49990,
      "due_date": "2025-01-15",
      "actions_taken": ["email_sent", "subscription_suspended"]
    },
    {
      "type": "overage_high",
      "severity": "medium",
      "tenant_id": "...",
      "tenant_name": "Empresa ABC",
      "message": "Overage de tokens al 250%",
      "overage_amount": 85000,
      "suggestion": "Considerar upgrade a plan superior"
    },
    {
      "type": "upsell_opportunity",
      "severity": "low",
      "tenant_id": "...",
      "tenant_name": "Startup DEF",
      "message": "Tenant usando 95% de cuota de agentes",
      "current_plan": "pro",
      "suggested_plan": "enterprise"
    }
  ]
}
```

---

## Dashboard de Ingresos

### Vista Ejecutiva (Admin Nivel 1)

#### KPIs Principales
```
┌─────────────────────────────────────────────────────┐
│  MRR            │  Nuevos Clientes │  Churn Rate    │
│  $8,500,000     │  +12             │  1.7%          │
│  ↑ 12.5%        │  ↑ 20%           │  ↓ 0.5%        │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Total Revenue  │  Overages        │  ARPT          │
│  $9,200,000     │  $700,000        │  $48,571       │
│  ↑ 15.2%        │  ↑ 25%           │  ↑ 8%          │
└─────────────────────────────────────────────────────┘
```

#### Gráfico: MRR Evolution (últimos 12 meses)
```
MRR (CLP)
10M │                                    ●
9M  │                              ●  ●
8M  │                         ●  ●
7M  │                    ●  ●
6M  │               ●  ●
5M  │          ●  ●
4M  │     ●  ●
    └───────────────────────────────────────
      F  M  A  M  J  J  A  S  O  N  D  E
```

#### Tabla: Top 10 Tenants por Ingresos
```
Tenant              | Plan       | MRR       | Overage  | Total    | Growth
--------------------|------------|-----------|----------|----------|--------
Empresa ABC         | Enterprise | $199,000  | $16,000  | $215,000 | +8%
Startup XYZ         | Pro        | $49,990   | $8,500   | $58,490  | +15%
Consultora DEF      | Enterprise | $299,000  | $0       | $299,000 | +2%
...
```

#### Distribución por Plan
```
Plan          | Tenants | % Total | MRR       | % MRR
--------------|---------|---------|-----------|-------
Básico        | 100     | 57%     | $1,999,000| 23%
Pro           | 60      | 34%     | $2,999,400| 35%
Enterprise    | 15      | 9%      | $3,500,000| 42%
```

### Vista por Tenant (Admin Nivel 1)

#### Perfil del Tenant
```
┌─────────────────────────────────────────────────────┐
│ Empresa ABC                                         │
│ Plan: Pro ($49,990/mes)                            │
│ Cliente desde: 01/06/2024 (8 meses)                │
│ Estado: Activo                                      │
└─────────────────────────────────────────────────────┘
```

#### Ingresos del Tenant
```
Mes Actual (Enero 2025)
├─ Plan Base:          $49,990
├─ Memory Overage:     $12,000  (2 GB adicionales)
├─ Token Overage:      $4,000   (200K tokens adicionales)
├─ Add-ons:            $0
├─ IVA (19%):          $12,538
└─ TOTAL:              $78,528

Histórico:
- Diciembre 2024: $49,990
- Noviembre 2024: $49,990
- Octubre 2024: $56,000
- Septiembre 2024: $49,990
- Total 2024: $425,000
- Lifetime Value: $503,528
```

#### Uso vs Límites
```
Memoria:  ████████░░ 3.5 GB / 5 GB (70%)
Tokens:   ████████░░ 1.2M / 1.5M (80%)
Agentes:  ███████░░░ 7 / 10 (70%)
Usuarios: ███████░░░ 18 / 25 (72%)
```

#### Facturas
```
Fecha      | Número      | Estado | Total     | Pagado el
-----------|-------------|--------|-----------|------------
31/01/2025 | INV-2025-01 | Pagada | $78,528   | 01/02/2025
31/12/2024 | INV-2024-12 | Pagada | $49,990   | 05/01/2025
30/11/2024 | INV-2024-11 | Pagada | $49,990   | 01/12/2024
```

#### Recomendaciones
```
[!] Oportunidad de Upsell
Este tenant está usando consistentemente >70% de sus límites.
Considera ofrecer upgrade a plan Enterprise.
Potencial adicional: $149,010/mes
```

### Reportes Automatizados

#### Reporte Mensual Ejecutivo (PDF)

Generado automáticamente el día 1 de cada mes:

**Contenido:**
1. Resumen Ejecutivo (1 página)
   - MRR actual y growth
   - Nuevos clientes y churn
   - Total revenue y desglose

2. Análisis de Ingresos (2 páginas)
   - Gráficos de evolución temporal
   - Distribución por plan
   - Top 10 tenants

3. Análisis de Uso (1 página)
   - Overages más frecuentes
   - Oportunidades de upsell

4. Salud Financiera (1 página)
   - Cuentas por cobrar
   - Pagos atrasados
   - Proyecciones próximo mes

#### Reporte Trimestral (Excel)

Exportable con todos los datos:
- Sheet 1: Resumen ejecutivo
- Sheet 2: Ingresos por tenant
- Sheet 3: Facturas emitidas
- Sheet 4: Pagos recibidos
- Sheet 5: Análisis de cohortes

---

## Implementación Backend

### Servicio: RevenueService

```python
# backend/app/modules/billing/revenue_service.py

from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy import func, and_
from app.models import Subscription, Invoice, Payment, RevenueEvent

class RevenueService:
    """Servicio para cálculo y análisis de ingresos."""

    async def get_mrr_summary(self) -> Dict:
        """Calcula MRR (Monthly Recurring Revenue) actual."""

        # Sumar base_price de todas las subscripciones activas
        result = await db.query(
            func.sum(Subscription.base_price).label('mrr'),
            func.count(Subscription.id).label('active_subs')
        ).filter(
            Subscription.status == 'active'
        ).first()

        current_mrr = result.mrr or 0
        active_subs = result.active_subs or 0

        # Calcular MRR del mes anterior para growth
        last_month_start = datetime.now().replace(day=1) - timedelta(days=1)
        last_month_start = last_month_start.replace(day=1)

        # ... calcular growth ...

        return {
            'mrr': current_mrr,
            'arr': current_mrr * 12,
            'active_subscriptions': active_subs,
            'average_revenue_per_tenant': current_mrr / active_subs if active_subs > 0 else 0,
            'growth': mrr_growth_percentage
        }

    async def get_revenue_by_tenant(
        self,
        from_date: datetime,
        to_date: datetime,
        page: int = 1,
        per_page: int = 20
    ) -> Dict:
        """Obtiene ingresos desglosados por tenant."""

        # Query compleja que une subscriptions, invoices, line_items
        query = db.query(
            Tenant.id,
            Tenant.name,
            Subscription.plan,
            Subscription.base_price,
            func.sum(
                case(
                    (InvoiceLineItem.item_type == 'memory_overage', InvoiceLineItem.amount),
                    else_=0
                )
            ).label('memory_overage'),
            func.sum(
                case(
                    (InvoiceLineItem.item_type == 'token_overage', InvoiceLineItem.amount),
                    else_=0
                )
            ).label('token_overage'),
            # ... más cálculos
        ).join(Subscription).join(Invoice).join(InvoiceLineItem).filter(
            and_(
                Invoice.issue_date >= from_date,
                Invoice.issue_date <= to_date,
                Invoice.status == 'paid'
            )
        ).group_by(
            Tenant.id, Tenant.name, Subscription.plan, Subscription.base_price
        ).order_by(
            func.sum(InvoiceLineItem.amount).desc()
        ).offset((page - 1) * per_page).limit(per_page)

        tenants = await query.all()

        # Formatear resultado
        return {
            'tenants': [
                {
                    'tenant_id': t.id,
                    'tenant_name': t.name,
                    'plan': t.plan,
                    'mrr': t.base_price,
                    'overage_revenue': t.memory_overage + t.token_overage,
                    'total_revenue': t.base_price + t.memory_overage + t.token_overage,
                    # ... más campos
                }
                for t in tenants
            ],
            'page': page,
            'per_page': per_page
        }

    async def calculate_overages(self, tenant_id: str) -> Dict:
        """Calcula overages del tenant para el período actual."""

        # Obtener subscription
        subscription = await db.query(Subscription).filter(
            Subscription.tenant_id == tenant_id,
            Subscription.status == 'active'
        ).first()

        if not subscription:
            return {'overages': []}

        # Obtener uso actual del tenant
        usage = await self._get_tenant_usage(tenant_id)

        overages = []

        # Memory overage
        if usage['memory_gb'] > subscription.included_memory_gb:
            excess_gb = usage['memory_gb'] - subscription.included_memory_gb
            cost = excess_gb * 5990  # $5,990 por GB adicional
            overages.append({
                'type': 'memory',
                'excess': excess_gb,
                'cost': cost,
                'description': f'{excess_gb:.2f} GB adicionales'
            })

        # Token overage
        if usage['tokens'] > subscription.included_tokens:
            excess_tokens = usage['tokens'] - subscription.included_tokens
            cost = (excess_tokens / 500000) * 9990  # $9,990 por 500K tokens
            overages.append({
                'type': 'tokens',
                'excess': excess_tokens,
                'cost': int(cost),
                'description': f'{excess_tokens:,} tokens adicionales'
            })

        return {
            'overages': overages,
            'total_overage_cost': sum(o['cost'] for o in overages)
        }

    async def generate_invoice_for_tenant(
        self,
        tenant_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> Invoice:
        """Genera factura para un tenant en un período."""

        subscription = await db.query(Subscription).filter(
            Subscription.tenant_id == tenant_id,
            Subscription.status == 'active'
        ).first()

        if not subscription:
            raise ValueError(f"No active subscription for tenant {tenant_id}")

        # Crear factura
        invoice_number = await self._generate_invoice_number()

        invoice = Invoice(
            tenant_id=tenant_id,
            subscription_id=subscription.id,
            invoice_number=invoice_number,
            status='pending',
            period_start=period_start,
            period_end=period_end,
            issue_date=datetime.now().date(),
            due_date=(datetime.now() + timedelta(days=15)).date()
        )

        # Agregar línea de plan base
        base_item = InvoiceLineItem(
            invoice_id=invoice.id,
            description=f"Plan {subscription.plan.title()} - {period_start.strftime('%B %Y')}",
            item_type='base_plan',
            quantity=1,
            unit_price=subscription.base_price,
            amount=subscription.base_price
        )

        # Calcular y agregar overages
        overages = await self.calculate_overages(tenant_id)
        overage_items = []

        for overage in overages['overages']:
            item = InvoiceLineItem(
                invoice_id=invoice.id,
                description=overage['description'],
                item_type=f"{overage['type']}_overage",
                quantity=overage['excess'],
                unit_price=overage['cost'] / overage['excess'],
                amount=overage['cost']
            )
            overage_items.append(item)

        # Calcular totales
        subtotal = subscription.base_price + overages['total_overage_cost']
        tax = int(subtotal * 0.19)  # IVA 19%
        total = subtotal + tax

        invoice.subtotal = subtotal
        invoice.tax = tax
        invoice.total = total
        invoice.amount_due = total

        # Guardar en BD
        db.add(invoice)
        db.add(base_item)
        for item in overage_items:
            db.add(item)

        await db.commit()

        return invoice
```

---

## Alertas Automáticas

### Configuración de Alertas

```python
# backend/app/modules/billing/alerts_service.py

class BillingAlertsService:
    """Servicio para detectar y enviar alertas de billing."""

    async def check_payment_failures(self):
        """Detecta pagos fallidos y envía alertas."""

        # Buscar invoices vencidas no pagadas
        overdue_invoices = await db.query(Invoice).filter(
            Invoice.status.in_(['pending', 'failed']),
            Invoice.due_date < datetime.now().date()
        ).all()

        for invoice in overdue_invoices:
            days_overdue = (datetime.now().date() - invoice.due_date).days

            if days_overdue >= 7:
                # Enviar recordatorio
                await self._send_payment_reminder(invoice)

            if days_overdue >= 14:
                # Suspender subscription
                await self._suspend_subscription(invoice.subscription_id)

    async def check_overage_opportunities(self):
        """Detecta tenants con overages altos (oportunidad de upsell)."""

        # Obtener tenants con overages > 50% del plan base
        # ... query ...

        for tenant in high_overage_tenants:
            await self._send_upsell_notification(tenant)

    async def check_churn_risk(self):
        """Detecta tenants en riesgo de cancelar."""

        # Factores de riesgo:
        # - Uso bajo (<30% de cuotas)
        # - Pagos atrasados recurrentes
        # - Reducción de actividad

        # ... análisis ...

        for tenant in at_risk_tenants:
            await self._notify_account_manager(tenant)
```

---

## Integración con Sistemas Externos

### Exportación para Contabilidad (SII Chile)

```python
# backend/app/modules/billing/export_service.py

class BillingExportService:
    """Servicio para exportar datos de facturación."""

    async def export_monthly_invoices_csv(self, year: int, month: int) -> str:
        """Exporta facturas del mes en formato CSV para contabilidad."""

        invoices = await db.query(Invoice).filter(
            extract('year', Invoice.issue_date) == year,
            extract('month', Invoice.issue_date) == month,
            Invoice.status == 'paid'
        ).all()

        # Generar CSV
        csv_content = "Fecha,Folio,RUT,Razon Social,Neto,IVA,Total\n"

        for inv in invoices:
            tenant = await db.query(Tenant).get(inv.tenant_id)
            csv_content += f"{inv.issue_date},{inv.sii_folio},{tenant.rut},{tenant.name},{inv.subtotal},{inv.tax},{inv.total}\n"

        return csv_content
```

---

## Conclusión

Este sistema de control de ingresos proporciona:

1. **Visibilidad Total**: Dashboard con KPIs en tiempo real
2. **Análisis Profundo**: Desglose por tenant, plan, período
3. **Automatización**: Generación de facturas y reportes automáticos
4. **Alertas Proactivas**: Detección de oportunidades y riesgos
5. **Integración**: Exportación para sistemas contables

El sistema está diseñado para escalar con el crecimiento del negocio y proporcionar insights accionables para maximizar ingresos y retención.
