# Sistemas de Pago Locales - Chile

Análisis de opciones de pago locales para el mercado chileno.

## 🇨🇱 Opciones Principales

### 1. Transbank ⭐ RECOMENDADO

**Proveedor:** Principal procesador de pagos de Chile (propiedad de bancos chilenos)

**Ventajas:**
- [OK] SDK oficial de Python: `transbank-sdk` (v6.1.0)
- [OK] Documentación completa en español
- [OK] Soporte para Webpay Plus (tarjetas débito/crédito)
- [OK] OneClick (pagos recurrentes con 1 click)
- [OK] Webpay Plus Mall (multi-comercio)
- [OK] Ambiente de integración y producción
- [OK] Mayor cobertura en Chile (usado por la mayoría de comercios)
- [OK] Soporte técnico local

**Productos disponibles:**
- **Webpay Plus**: Pagos únicos con tarjetas (débito/crédito)
- **Webpay Plus Mall**: Para marketplace con múltiples vendedores
- **OneClick**: Pagos recurrentes (suscripciones)
- **Transacción Completa**: Control total del flujo de pago

**Instalación:**
```bash
pip install transbank-sdk
```

**Ejemplo de integración:**
```python
from transbank.webpay.webpay_plus.transaction import Transaction

# Crear transacción
response = Transaction.create(
    buy_order="orden-12345",
    session_id="sesion-12345",
    amount=10000,  # CLP
    return_url="https://misitioweb.com/retorno"
)

# Confirmar transacción
result = Transaction.commit(token=token)
```

**URLs:**
- Documentación: https://www.transbankdevelopers.cl/
- GitHub: https://github.com/TransbankDevelopers/transbank-sdk-python
- API Reference: https://transbankdevelopers.cl/referencia/webpay?l=python
- PyPI: https://pypi.org/project/transbank-sdk/

**Costos típicos:**
- Comisión: ~2-4% por transacción (negociable según volumen)
- Sin costos mensuales fijos (depende del contrato)

---

### 2. Khipu

**Proveedor:** Plataforma de pagos bancarios directos (Chile, Argentina, Perú)

**Ventajas:**
- [OK] Pago directo desde cuenta bancaria (sin tarjeta)
- [OK] Menor comisión que tarjetas (~1.5-2%)
- [OK] Confirmación instantánea
- [OK] API REST bien documentada

**Desventajas:**
- [X] NO tiene SDK oficial de Python
- [X] Solo SDKs en Java, PHP, Ruby, .NET
- [X] Menor adopción que Transbank
- [X] Requiere que usuario tenga banca en línea

**Integración:**
Tendrías que usar su REST API directamente:
```python
import requests

# Crear cobro
response = requests.post(
    "https://khipu.com/api/2.0/payments",
    auth=(receiver_id, secret_key),
    data={
        "subject": "Pago de suscripción",
        "amount": 10000,
        "currency": "CLP",
        "return_url": "https://misitioweb.com/retorno"
    }
)
```

**URLs:**
- Documentación: https://docs.khipu.com/
- API: https://docs.khipu.com/payment-solutions/instant-payments/khipu-integration

**Costos típicos:**
- Comisión: ~1.5-2% por transacción
- Sin costos mensuales

---

## [+] Recomendación: Transbank

### Justificación:

1. **SDK Oficial Python** [OK]
   - Ahorra semanas de desarrollo
   - Mantenido por Transbank
   - Menos bugs, más seguro

2. **Mayor Cobertura** [OK]
   - Aceptado en 99% de comercios chilenos
   - Todos los bancos chilenos lo soportan
   - Usuarios familiarizados con Webpay

3. **Productos Completos** [OK]
   - Pagos únicos: Webpay Plus
   - Suscripciones: OneClick
   - Marketplace: Webpay Plus Mall

4. **Documentación Superior** [OK]
   - Docs en español
   - Ejemplos de código Python
   - Soporte técnico local

### Stack Propuesto:

```python
# requirements.txt
transbank-sdk==6.1.0
```

### Arquitectura de Integración:

```
┌─────────────┐
│   Tenant    │
│  Dashboard  │
└──────┬──────┘
       │ 1. Crear suscripción
       ▼
┌─────────────────────────────────┐
│  Backend FastAPI                │
│  /api/v1/payments/subscribe     │
└──────┬──────────────────────────┘
       │ 2. Transaction.create()
       ▼
┌─────────────────────────────────┐
│  Transbank SDK                  │
│  - Ambiente: Integración/Prod  │
└──────┬──────────────────────────┘
       │ 3. Token + URL de pago
       ▼
┌─────────────────────────────────┐
│  Webpay (Transbank)            │
│  - Usuario paga con tarjeta    │
└──────┬──────────────────────────┘
       │ 4. Redirect con token
       ▼
┌─────────────────────────────────┐
│  Backend /api/v1/payments/      │
│  confirm?token=xxx              │
│  - Transaction.commit()         │
│  - Activar tenant               │
└─────────────────────────────────┘
```

---

## [-] Plan de Implementación

### Fase 1: Ambiente de Integración
```python
# app/config.py
class Settings(BaseSettings):
    # Transbank
    TRANSBANK_ENV: str = "integration"  # o "production"
    TRANSBANK_COMMERCE_CODE: str
    TRANSBANK_API_KEY: str

    class Config:
        env_file = ".env"
```

### Fase 2: Servicio de Pagos
```python
# app/services/payment_service.py
from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.integration_type import IntegrationType

class PaymentService:
    def __init__(self, env: str = "integration"):
        if env == "production":
            Transaction.configure_for_production(
                commerce_code=settings.TRANSBANK_COMMERCE_CODE,
                api_key=settings.TRANSBANK_API_KEY
            )
        else:
            Transaction.configure_for_integration(
                commerce_code="597055555532",  # Código de prueba
                api_key="579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C"
            )

    async def create_subscription_payment(
        self,
        tenant_id: str,
        plan_id: str,
        amount: int
    ) -> dict:
        """Crear pago de suscripción"""
        buy_order = f"tenant-{tenant_id}-{int(time.time())}"
        session_id = f"session-{tenant_id}"

        response = Transaction.create(
            buy_order=buy_order,
            session_id=session_id,
            amount=amount,
            return_url=f"{settings.FRONTEND_URL}/payments/confirm"
        )

        # Guardar en DB
        await db.payment_intents.create({
            "tenant_id": tenant_id,
            "buy_order": buy_order,
            "token": response.token,
            "amount": amount,
            "status": "pending"
        })

        return {
            "token": response.token,
            "url": response.url
        }

    async def confirm_payment(self, token: str) -> dict:
        """Confirmar pago después de redirección"""
        response = Transaction.commit(token=token)

        # Verificar estado
        if response.status == "AUTHORIZED":
            # Actualizar DB
            intent = await db.payment_intents.find_one({"token": token})
            await db.payment_intents.update(
                {"token": token},
                {"status": "completed", "transaction_id": response.vci}
            )

            # Activar tenant
            await db.tenants.update(
                {"id": intent.tenant_id},
                {"status": "active", "subscription_status": "paid"}
            )

            return {"success": True, "transaction_id": response.vci}
        else:
            return {"success": False, "error": response.status}
```

### Fase 3: Endpoints REST
```python
# app/api/v1/payments.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])

class CreatePaymentRequest(BaseModel):
    plan_id: str
    amount: int

@router.post("/subscribe")
async def create_subscription_payment(
    request: CreatePaymentRequest,
    current_tenant: Tenant = Depends(get_current_tenant)
):
    """Crear pago de suscripción"""
    payment = await payment_service.create_subscription_payment(
        tenant_id=current_tenant.id,
        plan_id=request.plan_id,
        amount=request.amount
    )

    return {
        "token": payment["token"],
        "url": payment["url"]
    }

@router.get("/confirm")
async def confirm_payment(token: str):
    """Confirmar pago después de Webpay"""
    result = await payment_service.confirm_payment(token)

    if result["success"]:
        return {"message": "Pago confirmado", "transaction_id": result["transaction_id"]}
    else:
        raise HTTPException(status_code=400, detail="Pago rechazado")

@router.post("/webhooks/transbank")
async def transbank_webhook(request: Request):
    """Webhook para notificaciones de Transbank (OneClick)"""
    # Para pagos recurrentes
    pass
```

### Fase 4: Frontend (Next.js)
```typescript
// frontend/src/app/billing/subscribe/page.tsx
'use client'

export default function SubscribePage() {
  const [loading, setLoading] = useState(false)

  const handleSubscribe = async (planId: string, amount: number) => {
    setLoading(true)

    // Crear pago
    const response = await fetch('/api/v1/payments/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plan_id: planId, amount })
    })

    const { token, url } = await response.json()

    // Redirigir a Webpay
    window.location.href = url
  }

  return (
    <div>
      <h1>Planes de Suscripción</h1>

      <div className="grid grid-cols-3 gap-4">
        <PlanCard
          name="Básico"
          price={9990}
          features={["100k tokens/mes", "2 agentes"]}
          onSubscribe={() => handleSubscribe('basic', 9990)}
        />

        <PlanCard
          name="Pro"
          price={29990}
          features={["500k tokens/mes", "10 agentes"]}
          onSubscribe={() => handleSubscribe('pro', 29990)}
        />

        <PlanCard
          name="Enterprise"
          price={99990}
          features={["Ilimitado", "Agentes ilimitados"]}
          onSubscribe={() => handleSubscribe('enterprise', 99990)}
        />
      </div>
    </div>
  )
}
```

---

## [!] Seguridad

### Credenciales
```bash
# .env
TRANSBANK_ENV=integration  # o production
TRANSBANK_COMMERCE_CODE=597055555532
TRANSBANK_API_KEY=579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C
```

### Validación de Firmas
Transbank firma las respuestas - el SDK valida automáticamente.

### HTTPS Obligatorio
Transbank requiere HTTPS en producción.

---

## [=] Modelos de Suscripción

### Opción 1: Pago Único Mensual (Webpay Plus)
- Tenant paga cada mes manualmente
- Más simple de implementar
- Usuario debe recordar pagar

### Opción 2: Suscripción Automática (OneClick)
- Se guarda tarjeta (tokenizada)
- Cobro automático cada mes
- Requiere autorización inicial del usuario
- Mejor experiencia de usuario

**Recomendación inicial:** Empezar con Webpay Plus (opción 1), luego agregar OneClick.

---

## [T] Testing

### Tarjetas de Prueba (Ambiente Integración):

**VISA:**
- Número: 4051 8856 0044 6623
- CVV: 123
- Fecha: Cualquier fecha futura

**Mastercard:**
- Número: 5186 0595 3829 4913
- CVV: 123
- Fecha: Cualquier fecha futura

**Resultado:** Todas aprueban

### RUT de Prueba:
- 11.111.111-1 (Acepta)
- 22.222.222-2 (Rechaza)

---

## [^] Próximos Pasos

1. [OK] Instalar SDK: `pip install transbank-sdk`
2. [OK] Configurar ambiente de integración
3. [OK] Implementar servicio de pagos
4. [OK] Crear endpoints REST
5. [OK] Implementar UI de suscripción
6. [OK] Probar con tarjetas de prueba
7. [OK] Solicitar credenciales de producción a Transbank
8. [OK] Deploy a producción

**Tiempo estimado:** 1-2 semanas para implementación completa.
