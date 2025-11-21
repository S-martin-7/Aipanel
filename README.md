# AIPanel - Sistema de Gestión Multi-Tenant para Agentes AI

Panel de control administrativo para gestionar servidores, tenants, APIKeys, pagos y agentes AI personalizados con modelos OpenAI GPT-5 y Claude.

## 🚀 Características Principales

### Sistema Multi-Nivel
- **Nivel 1**: Servidores con APIKEY principal
- **Nivel 2**: Tenants (clientes) con configuración individual

### Gestión de APIKeys
- Generación y rotación automática
- Activación/bloqueo dinámico
- Control de acceso por tenant

### Control de Pagos
- Integración con Stripe/Mercadopago
- Cartola detallada por cliente
- Suspensión automática por falta de pago
- Sistema de alertas y recordatorios

### Agentes AI Personalizados
- **GPT-5-Mini**: Texto, visión, imágenes, documentos, OCR
- **GPT-Realtime-Mini**: Audio en tiempo real, bots de voz, llamadas telefónicas
- **Claude Sonnet 4.5**: Alternativa para procesamiento de texto
- Memoria de largo plazo
- Auto-aprendizaje
- Fuentes de datos: PDFs, páginas web, APIs

### Métricas y Monitoreo
- Uso de tokens en tiempo real
- Costos desglosados por modelo
- Alertas de cuota y límites
- Dashboard con gráficos interactivos

## 🏗️ Arquitectura

```
┌─────────────────────────────────────┐
│      Frontend (Next.js 14)          │
│   Panel de Control Administrativo   │
└─────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│      Backend API (NestJS)           │
│   Gateway + Autenticación           │
└─────────────────────────────────────┘
                 │
     ┌───────────┼───────────┐
     ▼           ▼           ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│PostgreSQL│ │  Redis  │ │   S3    │
└─────────┘ └─────────┘ └─────────┘
```

## 📂 Estructura del Proyecto

```
/
├── backend/              # API NestJS
│   └── src/
│       ├── modules/      # Módulos funcionales
│       │   ├── auth/     # Autenticación/Autorización
│       │   ├── servers/  # Gestión de servidores
│       │   ├── tenants/  # Gestión de tenants
│       │   ├── agents/   # Gestión de agentes AI
│       │   ├── payments/ # Sistema de pagos
│       │   ├── usage/    # Métricas de uso
│       │   └── data-sources/ # Fuentes de datos
│       ├── common/       # Utilidades compartidas
│       └── config/       # Configuración
├── frontend/             # Panel Admin Next.js
│   └── src/
│       ├── app/          # App Router
│       ├── components/   # Componentes React
│       └── lib/          # Librerías y utils
├── prisma/               # Schemas de base de datos
├── shared/               # Tipos y utils compartidos
├── docs/                 # Documentación
```

## 🛠️ Stack Tecnológico (Python-First)

### Backend (100% Python)
- **Framework**: FastAPI + Uvicorn
- **Lenguaje**: Python 3.11
- **Base de Datos**: PostgreSQL 15+
- **ORM**: SQLAlchemy 2.0 + Alembic
- **Validación**: Pydantic v2
- **Cache**: Redis 7+
- **Tasks**: Celery + Redis
- **Auth**: python-jose + passlib
- **App Server**: Gunicorn + Uvicorn workers

### Frontend
- **Framework**: Next.js 14+ (App Router)
- **Lenguaje**: TypeScript
- **UI**: Tailwind CSS + Shadcn/ui
- **Estado**: Zustand
- **Charts**: Recharts
- **Formularios**: React Hook Form + Zod

### Infraestructura
- **Reverse Proxy**: Nginx
- **SSL**: Let's Encrypt (Certbot)
- **Deployment**: Nativo (sin Docker)
- **Process Manager**: Systemd (nativo Linux)
- **Monitoring**: Prometheus + Sentry

### Servicios Externos
- **Pagos**: Stripe (stripe-python)
- **AI**: OpenAI SDK + Anthropic SDK (oficiales)
- **Storage**: boto3 (AWS S3)
- **Email**: SendGrid o Resend

## 🎯 Por Qué Python + Sin Docker

Este proyecto usa **Python para el backend** y **deployment nativo**:

**Python-First:**
- ✅ **Mejor para AI**: Ecosistema nativo de OpenAI/Anthropic
- ✅ **Type-Safe**: Pydantic + mypy = validación robusta
- ✅ **Maduro**: Librerías probadas en producción
- ✅ **Performance**: FastAPI tan rápido como Node.js
- ✅ **Menos Fragmentación**: Un solo lenguaje para backend

**Sin Docker:**
- ✅ **Menor consumo de recursos**: Ahorra ~200-300MB RAM
- ✅ **Más eficiente**: Ideal para 2-3 apps por servidor
- ✅ **Más simple**: Debugging directo, sin capas
- ✅ **Systemd**: Gestor nativo de Linux, muy eficiente

## 🚦 Getting Started

### Prerrequisitos
- VPS con Ubuntu 20.04+ o Debian 11+
- Mínimo 2GB RAM, 2 vCPUs
- Node.js 20+ (se instala automáticamente)
- PostgreSQL 15+ (se instala automáticamente)
- Redis 7+ (se instala automáticamente)
- Nginx (se instala automáticamente)

### Instalación Rápida

1. Clonar el repositorio
```bash
cd /var/www
git clone <repo-url> aipanel
cd aipanel
```

2. Ejecutar script de instalación automática
```bash
# Instala todas las dependencias del sistema y del proyecto
bash install.sh
```

3. Configurar API Keys
```bash
nano .env
```

Edita las siguientes variables:
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `STRIPE_SECRET_KEY`
- `AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY`
- Dominios: `FRONTEND_URL` y `NEXT_PUBLIC_API_URL`

4. Desplegar en producción
```bash
# Construye las apps e inicia con PM2
bash deploy.sh
```

5. Configurar Nginx y SSL
```bash
# Copiar configuración de Nginx
sudo cp nginx.conf /etc/nginx/sites-available/aipanel
sudo ln -s /etc/nginx/sites-available/aipanel /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Obtener certificados SSL
sudo certbot --nginx -d aipanel.tudominio.com -d api.aipanel.tudominio.com
```

### Acceder al panel
- Frontend: https://aipanel.tudominio.com
- Backend API: https://api.aipanel.tudominio.com
- API Docs: https://api.aipanel.tudominio.com/api/docs

### Gestión con Systemd
```bash
sudo systemctl status aipanel-api      # Ver estado
sudo journalctl -u aipanel-api -f      # Ver logs en tiempo real
sudo systemctl restart aipanel-api     # Reiniciar servicio
sudo systemctl status 'aipanel-*'      # Ver todos los servicios
```

## 📊 Modelos AI Soportados

### OpenAI
- **gpt-5-mini**: Texto + Visión + Imágenes + Documentos
- **gpt-realtime-mini**: Audio en tiempo real + Voz
- **gpt-5**: Modelo completo (opcional)
- **o3-mini**: Razonamiento optimizado

### Anthropic Claude
- **claude-sonnet-4.5**: Texto de alta calidad
- **claude-opus-4**: Tareas complejas
- **claude-haiku-4**: Respuestas rápidas

## 💳 Sistema de Facturación

### Planes Disponibles
- **Free**: $0 - 1K tokens/mes
- **Starter**: $29 - 100K tokens/mes
- **Professional**: $99 - 500K tokens/mes
- **Business**: $299 - 2M tokens/mes
- **Enterprise**: Personalizado

### Reglas de Suspensión
- Pago vencido > 7 días: Recordatorio automático
- Pago vencido > 14 días: Suspensión automática
- Cuota excedida: Throttling o suspensión (configurable)
- Reactivación automática al pagar

## 📖 Documentación

- [Guía de Deployment](./docs/DEPLOYMENT.md) - **IMPORTANTE: Lee esto primero**
- [Stack Tecnológico Python](./docs/architecture/TECH_STACK.md) - Decisiones técnicas
- [Arquitectura de Autenticación](./docs/architecture/AUTHENTICATION.md)
- [Arquitectura del Sistema](./docs/architecture/ARCHITECTURE.md)
- [API Reference](./docs/api/API.md)
- [Guía de Modelos AI](./docs/AI_MODELS.md)
- [Sistema de Pagos](./docs/PAYMENTS.md)

## 🔐 Seguridad

- Autenticación JWT con refresh tokens
- APIKeys encriptadas en base de datos
- Rate limiting por tenant
- Validación de entrada con class-validator
- CORS configurado
- Helmet para headers de seguridad

## 📝 Licencia

MIT

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor abre un issue primero para discutir los cambios.

---

Desarrollado para gestión profesional de agentes AI multi-tenant
