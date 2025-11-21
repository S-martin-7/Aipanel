# AIPanel - Sistema de Gestión Multi-Tenant para Agentes AI

Panel de control administrativo para gestionar servidores, tenants, APIKeys, pagos y agentes AI personalizados con modelos OpenAI GPT-5 y Claude.

## [*] Características Principales

### Sistema Multi-Nivel
- **Nivel 1**: Servidores con APIKEY principal
- **Nivel 2**: Tenants (clientes) con configuración individual

### Gestión de APIKeys
- Generación y rotación automática
- Activación/bloqueo dinámico
- Control de acceso por tenant

### Control de Pagos (Chile)
- Integración con Transbank (Webpay Plus, OneClick)
- Pagos con tarjetas de débito/crédito chilenas
- Suscripciones automáticas
- Cartola detallada por cliente
- Suspensión automática por falta de pago
- Sistema de alertas y recordatorios

### Agentes AI Personalizados
- **GPT-5-Mini**: Texto, visión, imágenes, documentos, OCR
- **GPT-Realtime-Mini**: Audio en tiempo real, bots de voz, llamadas telefónicas
- **Claude Sonnet 4.5**: Alternativa para procesamiento de texto
- **Memoria Inteligente**: Resúmenes automáticos multi-nivel (sin vector stores)
- **Auto-aprendizaje**: Análisis de conversaciones y feedback
- **Fuentes de datos**: PDFs, páginas web, documentos Word, imágenes (OCR)
- **Búsqueda híbrida**: Full-text search + keywords + tópicos

### Métricas y Monitoreo
- Uso de tokens en tiempo real
- Costos desglosados por modelo
- Alertas de cuota y límites
- Dashboard con gráficos interactivos

## [!] Por Qué AIPanel vs ChatGPT Pro

AIPanel no compite en modelos de IA (usamos GPT-4o, GPT-5-mini, Claude), sino en el **ecosistema empresarial, automatización, memoria persistente real e integraciones**.

### Diferenciadores Clave

1. **Memoria Persistente Real**: Ilimitada por tenant, cada agente tiene su propia memoria independiente medida en GB
2. **Arquitectura Multi-Tenant**: Aislamiento completo entre clientes con API keys independientes y facturación por tenant
3. **Agentes Autónomos**: Workers 24/7 en segundo plano, procesamiento asíncrono, tareas programadas
4. **Integraciones Reales**: WhatsApp Business, SMS, Email, Asterisk/FreePBX, ERPs (Odoo, SAP), CRMs (Salesforce, HubSpot)
5. **RAG Avanzado**: PDFs pesados (100+ MB), OCR integrado, extracción de tablas y gráficos, resúmenes automáticos multinivel
6. **Modelos Personalizables**: Cada agente puede usar un modelo diferente con configuración de temperatura y max_tokens
7. **Telefonía AI**: IVR con reconocimiento de voz, voice bots 24/7, grabación y transcripción de llamadas
8. **Control Total de Datos**: Hosting local, cumplimiento con regulaciones locales, backups controlados
9. **Facturación Local (Chile)**: Transbank, Khipu, facturación en CLP, facturación electrónica SII
10. **Auditoría Empresarial**: Logs completos, métricas de uso por tenant/agente, reportes de costos, tracking de tokens
11. **Automatización Empresarial**: Flujos de trabajo programables, triggers y acciones automáticas, procesamiento batch
12. **Agentes Especializados**: Pre-configurados por industria (legal, salud, retail, educación, finanzas)

### Casos de Uso Únicos

- **Call Center AI 24/7**: Atender llamadas telefónicas, transferir a humanos, registrar en CRM
- **Sistema Multi-Cliente**: Agencias que dan servicio a múltiples clientes con aislamiento total
- **WhatsApp Bot Empresarial**: Responder consultas, tomar pedidos, actualizar CRM en tiempo real
- **Integración ERP**: Consultar stock, crear órdenes de compra, actualizar inventario
- **Auditoría Legal**: Revisar cientos de contratos, extraer cláusulas clave, generar matriz de riesgos

Ver documentación completa en [docs/DIFFERENTIATORS.md](docs/DIFFERENTIATORS.md)

## [#] Arquitectura

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

## [...] Estructura del Proyecto

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

## [>] Stack Tecnológico (Python-First)

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
- **Pagos**: Transbank SDK (pagos locales Chile)
- **AI**: OpenAI SDK + Anthropic SDK (oficiales)
- **Storage**: boto3 (AWS S3) o almacenamiento local
- **Email**: SendGrid o Resend
- **Procesamiento**: PyPDF2, pdfplumber, pytesseract (OCR)

## [+] Por Qué Python + Sin Docker

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
- `TRANSBANK_COMMERCE_CODE` y `TRANSBANK_API_KEY`
- `TRANSBANK_ENV` (integration o production)
- `AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY` (opcional)
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

## [=] Modelos AI Soportados

### OpenAI
- **gpt-5-mini**: Texto + Visión + Imágenes + Documentos
- **gpt-realtime-mini**: Audio en tiempo real + Voz
- **gpt-5**: Modelo completo (opcional)
- **o3-mini**: Razonamiento optimizado

### Anthropic Claude
- **claude-sonnet-4.5**: Texto de alta calidad
- **claude-opus-4**: Tareas complejas
- **claude-haiku-4**: Respuestas rápidas

## [$] Sistema de Facturación

### Planes Disponibles

| Plan | Precio (CLP) | Memoria | Agentes | Tokens/Mes | Usuarios |
|------|--------------|---------|---------|------------|----------|
| **Básico** | $19,990 | 1 GB | 2 | 250K | 5 |
| **Pro** | $49,990 | 5 GB | 10 | 1.5M | 25 |
| **Enterprise** | Desde $199,000 | 20+ GB | Ilimitados | 10M+ | 100+ |

### Características por Plan

- **Básico**: Ideal para emprendedores y startups. Incluye API REST, webhooks básicos, 1 integración externa
- **Pro**: Para empresas en crecimiento. RAG avanzado, telefonía AI (500 min), hasta 5 integraciones, soporte prioritario
- **Enterprise**: Para grandes empresas. Agentes ilimitados, integraciones ilimitadas, soporte 24/7, SLA 99.9%

### Métodos de Pago (Chile)
- Transbank Webpay Plus (tarjetas chilenas)
- Transferencia bancaria
- Khipu (cuentas RUT)
- Facturación electrónica automática (SII)

Ver planes detallados en [docs/PRICING_PLANS.md](docs/PRICING_PLANS.md)

## [?] Documentación

### Documentos Comerciales
- [Diferenciadores vs ChatGPT Pro](./docs/DIFFERENTIATORS.md) - Por qué AIPanel es diferente
- [Planes Comerciales](./docs/PRICING_PLANS.md) - Precios, features y add-ons detallados
- [Control de Ingresos](./docs/REVENUE_CONTROL.md) - Sistema de facturación y análisis de ingresos por tenant

### Documentos Técnicos
- [Guía de Deployment](./docs/DEPLOYMENT.md) - **IMPORTANTE: Lee esto primero**
- [Especificaciones Técnicas](./TECHNICAL_SPECIFICATIONS.md) - Esquema completo del sistema
- [Guía de Desarrollo](./DEVELOPMENT_GUIDE.md) - Cómo crear nuevos módulos
- [Estructura del Proyecto](./PROJECT_STRUCTURE.md) - Arquitectura modular
- [Onboarding de Desarrolladores](./DEVELOPER_ONBOARDING.md) - Primer día en el proyecto
- [Asignación de Tareas](./TASK_ASSIGNMENTS.md) - Sprints y tareas detalladas

### Arquitectura y Decisiones
- [Stack Tecnológico Python](./docs/architecture/TECH_STACK.md) - Decisiones técnicas
- [Arquitectura de Autenticación](./docs/architecture/AUTHENTICATION.md) - Multi-nivel
- [Sistema de Tracking de Tokens](./docs/architecture/TOKEN_TRACKING.md) - Uso justo
- [Sistemas de Pago Chile](./docs/architecture/PAYMENT_SYSTEMS_CHILE.md) - Transbank vs Khipu
- [Estrategia de Memoria](./docs/architecture/MEMORY_STRATEGY.md) - Resúmenes vs Vector Stores
- [Estrategia de Almacenamiento](./docs/architecture/STORAGE_STRATEGY.md) - S3 vs Base de Datos
- [Análisis de Gaps](./docs/ANALYSIS_GAPS.md) - Estado del proyecto

## [!] Seguridad

- Autenticación JWT con refresh tokens
- APIKeys encriptadas en base de datos
- Rate limiting por tenant
- Validación de entrada con class-validator
- CORS configurado
- Helmet para headers de seguridad

## 📝 Licencia

MIT

## [&] Contribuir

Las contribuciones son bienvenidas. Por favor abre un issue primero para discutir los cambios.

---

Desarrollado para gestión profesional de agentes AI multi-tenant
