# Arquitectura de Autenticación - AIPanel

Sistema de autenticación multi-nivel para control granular de acceso entre administradores del sistema y usuarios tenant.

## [#] Arquitectura de Dos Niveles

```
┌─────────────────────────────────────────────────────────┐
│                    NIVEL 1: ADMINS                       │
│  Super Admin / Admin - Gestión Global del Sistema       │
│  - Crear/editar/eliminar Servidores                     │
│  - Crear/editar/eliminar Tenants                        │
│  - Ver todas las métricas y pagos                       │
│  - Control total del sistema                            │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                  NIVEL 2: TENANT USERS                   │
│  Usuarios de Tenant - Gestión de sus Agentes           │
│  - Ver solo SU tenant                                   │
│  - Gestionar SUS agentes AI                             │
│  - Ver SUS métricas y costos                            │
│  - Configurar SUS fuentes de datos                      │
└─────────────────────────────────────────────────────────┘
```

## [?] Roles del Sistema

### Nivel 1: Administradores

```typescript
enum AdminRole {
  SUPER_ADMIN = 'SUPER_ADMIN',  // Control total
  ADMIN = 'ADMIN',                // Gestión de servidores y tenants
  SUPPORT = 'SUPPORT',            // Solo lectura, soporte
}
```

**Permisos de SUPER_ADMIN:**
- [OK] CRUD completo de usuarios admin
- [OK] CRUD completo de servidores
- [OK] CRUD completo de tenants
- [OK] Ver todas las métricas financieras
- [OK] Configuración global del sistema
- [OK] Logs de auditoría completos

**Permisos de ADMIN:**
- [OK] CRUD de servidores (asignados a él)
- [OK] CRUD de tenants (asignados a él)
- [OK] Ver métricas de sus servidores
- [X] No puede crear otros admins
- [X] No puede modificar configuración global

**Permisos de SUPPORT:**
- [OK] Ver servidores y tenants (solo lectura)
- [OK] Ver tickets de soporte
- [X] No puede modificar nada
- [X] No puede ver información financiera sensible

### Nivel 2: Usuarios Tenant

```typescript
enum TenantRole {
  OWNER = 'OWNER',          // Dueño del tenant
  ADMIN = 'ADMIN',          // Administrador del tenant
  DEVELOPER = 'DEVELOPER',  // Desarrollador con acceso a APIs
  VIEWER = 'VIEWER',        // Solo lectura
}
```

**Permisos de OWNER:**
- [OK] CRUD completo de usuarios del tenant
- [OK] CRUD completo de agentes
- [OK] CRUD completo de fuentes de datos
- [OK] Configurar métodos de pago
- [OK] Ver facturación y cartola
- [OK] Rotar APIKey del tenant

**Permisos de ADMIN:**
- [OK] CRUD de agentes
- [OK] CRUD de fuentes de datos
- [OK] Ver métricas de uso
- [X] No puede gestionar usuarios
- [X] No puede ver facturación completa

**Permisos de DEVELOPER:**
- [OK] Usar agentes vía API
- [OK] Ver documentación de API
- [OK] Ver métricas de uso
- [X] No puede crear agentes
- [X] No puede modificar configuración

**Permisos de VIEWER:**
- [OK] Ver agentes
- [OK] Ver métricas básicas
- [X] No puede modificar nada

## [?] Flujo de Autenticación

### Flujo Admin (Nivel 1)

```
┌────────────────────────────────────────────────────────┐
│ 1. Login Admin                                         │
│    POST /api/auth/admin/login                         │
│    Body: { email, password }                          │
└────────────────────────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│ 2. Validación                                          │
│    - Verificar email existe en tabla `User`           │
│    - Verificar password con bcrypt                    │
│    - Verificar role es SUPER_ADMIN, ADMIN o SUPPORT   │
└────────────────────────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│ 3. Generar Tokens                                      │
│    - Access Token (JWT): 15 minutos                   │
│    - Refresh Token (JWT): 7 días                      │
│    - Payload: { userId, email, role, type: 'admin' }  │
└────────────────────────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│ 4. Respuesta                                           │
│    {                                                   │
│      accessToken: "eyJ...",                           │
│      refreshToken: "eyJ...",                          │
│      user: { id, email, name, role }                  │
│    }                                                   │
└────────────────────────────────────────────────────────┘
```

### Flujo Tenant (Nivel 2)

```
┌────────────────────────────────────────────────────────┐
│ 1. Login Tenant User                                   │
│    POST /api/auth/tenant/login                        │
│    Body: { email, password }                          │
└────────────────────────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│ 2. Validación                                          │
│    - Verificar email existe en tabla `TenantUser`     │
│    - Verificar password con bcrypt                    │
│    - Verificar tenant está ACTIVE                     │
│    - Verificar payment status no es OVERDUE           │
└────────────────────────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│ 3. Generar Tokens                                      │
│    - Access Token: 15 minutos                         │
│    - Refresh Token: 7 días                            │
│    - Payload: {                                        │
│        userId,                                         │
│        tenantId,                                       │
│        role,                                           │
│        type: 'tenant'                                  │
│      }                                                 │
└────────────────────────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│ 4. Respuesta                                           │
│    {                                                   │
│      accessToken: "eyJ...",                           │
│      refreshToken: "eyJ...",                          │
│      user: {                                          │
│        id, email, name, role,                         │
│        tenant: { id, name, status }                   │
│      }                                                 │
│    }                                                   │
└────────────────────────────────────────────────────────┘
```

## [?] Modelo de Datos Actualizado

```prisma
// Admin Users (Nivel 1)
model User {
  id            String    @id @default(cuid())
  email         String    @unique
  password      String    // bcrypt hashed
  name          String
  role          AdminRole @default(ADMIN)
  isActive      Boolean   @default(true)

  // Auditoría
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt
  lastLoginAt   DateTime?

  // Refresh tokens
  refreshTokens RefreshToken[]

  @@map("users")
}

enum AdminRole {
  SUPER_ADMIN
  ADMIN
  SUPPORT
}

// Tenant Users (Nivel 2)
model TenantUser {
  id            String      @id @default(cuid())
  tenantId      String
  email         String      @unique
  password      String      // bcrypt hashed
  name          String
  role          TenantRole  @default(VIEWER)
  isActive      Boolean     @default(true)

  // Relaciones
  tenant        Tenant      @relation(fields: [tenantId], references: [id], onDelete: Cascade)

  // Auditoría
  createdAt     DateTime    @default(now())
  updatedAt     DateTime    @updatedAt
  lastLoginAt   DateTime?

  // Refresh tokens
  refreshTokens RefreshToken[]

  @@index([tenantId])
  @@map("tenant_users")
}

enum TenantRole {
  OWNER
  ADMIN
  DEVELOPER
  VIEWER
}

// Refresh Tokens (para ambos niveles)
model RefreshToken {
  id          String    @id @default(cuid())
  token       String    @unique

  // Usuario puede ser Admin o TenantUser
  userId      String?
  tenantUserId String?

  user        User?     @relation(fields: [userId], references: [id], onDelete: Cascade)
  tenantUser  TenantUser? @relation(fields: [tenantUserId], references: [id], onDelete: Cascade)

  expiresAt   DateTime
  createdAt   DateTime  @default(now())

  @@index([token])
  @@map("refresh_tokens")
}

// Logs de auditoría
model AuditLog {
  id          String   @id @default(cuid())

  // Quién hizo la acción
  userId      String?
  tenantUserId String?
  userType    String   // 'admin' | 'tenant'
  userEmail   String

  // Qué hizo
  action      String   // 'CREATE', 'UPDATE', 'DELETE', 'LOGIN', etc.
  resource    String   // 'server', 'tenant', 'agent', etc.
  resourceId  String?

  // Detalles
  changes     Json?    // Cambios realizados
  metadata    Json?    // Información adicional

  // IP y User Agent
  ipAddress   String?
  userAgent   String?

  createdAt   DateTime @default(now())

  @@index([userId])
  @@index([tenantUserId])
  @@index([action])
  @@index([createdAt])
  @@map("audit_logs")
}
```

## [?] Middleware y Guards

### JWT Strategy

```typescript
// Admin JWT Strategy
@Injectable()
export class AdminJwtStrategy extends PassportStrategy(Strategy, 'admin-jwt') {
  constructor() {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      secretOrKey: process.env.JWT_SECRET,
    });
  }

  async validate(payload: any) {
    if (payload.type !== 'admin') {
      throw new UnauthorizedException('Invalid token type');
    }

    return {
      userId: payload.userId,
      email: payload.email,
      role: payload.role,
      type: 'admin',
    };
  }
}

// Tenant JWT Strategy
@Injectable()
export class TenantJwtStrategy extends PassportStrategy(Strategy, 'tenant-jwt') {
  constructor() {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      secretOrKey: process.env.JWT_SECRET,
    });
  }

  async validate(payload: any) {
    if (payload.type !== 'tenant') {
      throw new UnauthorizedException('Invalid token type');
    }

    return {
      userId: payload.userId,
      tenantId: payload.tenantId,
      email: payload.email,
      role: payload.role,
      type: 'tenant',
    };
  }
}
```

### Guards de Autorización

```typescript
// Admin Only Guard
@Injectable()
export class AdminGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest();
    const user = request.user;

    if (!user || user.type !== 'admin') {
      throw new ForbiddenException('Admin access required');
    }

    return true;
  }
}

// Super Admin Only Guard
@Injectable()
export class SuperAdminGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest();
    const user = request.user;

    if (!user || user.type !== 'admin' || user.role !== 'SUPER_ADMIN') {
      throw new ForbiddenException('Super Admin access required');
    }

    return true;
  }
}

// Tenant Guard (con verificación de tenant)
@Injectable()
export class TenantGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest();
    const user = request.user;

    if (!user || user.type !== 'tenant') {
      throw new ForbiddenException('Tenant access required');
    }

    // Verificar que el recurso solicitado pertenece al tenant
    const resourceTenantId = request.params.tenantId || request.body.tenantId;
    if (resourceTenantId && resourceTenantId !== user.tenantId) {
      throw new ForbiddenException('Access denied to this tenant resource');
    }

    return true;
  }
}

// Role-based Guard (flexible)
@Injectable()
export class RolesGuard implements CanActivate {
  constructor(private reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    const requiredRoles = this.reflector.get<string[]>('roles', context.getHandler());
    if (!requiredRoles) {
      return true;
    }

    const request = context.switchToHttp().getRequest();
    const user = request.user;

    return requiredRoles.includes(user.role);
  }
}
```

### Decoradores Personalizados

```typescript
// Decorador para requerir roles específicos
export const Roles = (...roles: string[]) => SetMetadata('roles', roles);

// Decorador para obtener el usuario actual
export const CurrentUser = createParamDecorator(
  (data: unknown, ctx: ExecutionContext) => {
    const request = ctx.switchToHttp().getRequest();
    return request.user;
  },
);

// Decorador para obtener el tenant actual
export const CurrentTenant = createParamDecorator(
  (data: unknown, ctx: ExecutionContext) => {
    const request = ctx.switchToHttp().getRequest();
    return request.user?.tenantId;
  },
);
```

## [?] Endpoints de Autenticación

### Admin Endpoints

```typescript
// Admin Login
POST /api/auth/admin/login
Body: { email: string, password: string }
Response: { accessToken, refreshToken, user }

// Admin Register (solo SUPER_ADMIN puede crear)
POST /api/auth/admin/register
Headers: { Authorization: Bearer <token> }
Body: { email, password, name, role }
Response: { user }

// Refresh Token
POST /api/auth/admin/refresh
Body: { refreshToken: string }
Response: { accessToken, refreshToken }

// Logout
POST /api/auth/admin/logout
Headers: { Authorization: Bearer <token> }
Body: { refreshToken: string }
Response: { success: true }

// Get Current User
GET /api/auth/admin/me
Headers: { Authorization: Bearer <token> }
Response: { user }
```

### Tenant Endpoints

```typescript
// Tenant User Login
POST /api/auth/tenant/login
Body: { email: string, password: string }
Response: { accessToken, refreshToken, user, tenant }

// Tenant User Register (solo OWNER puede crear)
POST /api/auth/tenant/register
Headers: { Authorization: Bearer <token> }
Body: { email, password, name, role }
Response: { user }

// Refresh Token
POST /api/auth/tenant/refresh
Body: { refreshToken: string }
Response: { accessToken, refreshToken }

// Logout
POST /api/auth/tenant/logout
Headers: { Authorization: Bearer <token> }
Body: { refreshToken: string }
Response: { success: true }

// Get Current User
GET /api/auth/tenant/me
Headers: { Authorization: Bearer <token> }
Response: { user, tenant }
```

## [!] Seguridad y Mejores Prácticas

### Password Hashing

```typescript
import * as bcrypt from 'bcrypt';

// Hash password
const saltRounds = 12;
const hashedPassword = await bcrypt.hash(plainPassword, saltRounds);

// Verify password
const isValid = await bcrypt.compare(plainPassword, hashedPassword);
```

### JWT Configuration

```env
# .env
JWT_SECRET=<strong-random-secret-32-chars>
JWT_REFRESH_SECRET=<different-strong-secret>
JWT_EXPIRES_IN=15m
JWT_REFRESH_EXPIRES_IN=7d
```

### Rate Limiting

```typescript
// Limitar intentos de login
@UseGuards(ThrottlerGuard)
@Throttle(5, 60) // 5 intentos por minuto
@Post('login')
async login(@Body() loginDto: LoginDto) {
  // ...
}
```

### Logout Seguro

1. Invalidar refresh token en base de datos
2. Cliente elimina tokens del localStorage
3. Opcional: Blacklist de access tokens (con Redis TTL)

### Rotación de Refresh Tokens

Cada vez que se usa un refresh token, generar uno nuevo y invalidar el anterior.

## [=] Dashboard por Nivel

### Dashboard Admin (Nivel 1)

**Ruta:** `/admin/dashboard`

**Acceso:** Solo usuarios con `type: 'admin'`

**Vistas:**
- Servidores totales, activos, suspendidos
- Tenants totales, activos, con pagos pendientes
- Ingresos mensuales/anuales
- Gráficos de uso global
- Alertas críticas del sistema

### Dashboard Tenant (Nivel 2)

**Ruta:** `/dashboard`

**Acceso:** Solo usuarios con `type: 'tenant'`

**Vistas:**
- Agentes del tenant
- Uso de tokens del mes
- Balance y próximo pago
- Métricas de costos
- Configuración del tenant

## [?] Manejo de Suspensiones

### Tenant Suspendido

Si un tenant está suspendido (`status: 'SUSPENDED'`):

1. **Login:** [X] Bloqueado con mensaje: "Tu cuenta está suspendida por falta de pago"
2. **API Calls:** [X] Rechazados con error 403
3. **Dashboard:** [!] Acceso limitado solo a ver facturación y pagar

```typescript
@Injectable()
export class TenantStatusGuard implements CanActivate {
  constructor(private prisma: PrismaService) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest();
    const user = request.user;

    if (user.type !== 'tenant') {
      return true; // No aplica para admins
    }

    const tenant = await this.prisma.tenant.findUnique({
      where: { id: user.tenantId },
      select: { status: true },
    });

    if (tenant.status === 'SUSPENDED' || tenant.status === 'BLOCKED') {
      throw new ForbiddenException(
        'Your account is suspended. Please contact support or update your payment method.'
      );
    }

    return true;
  }
}
```

## [?] Auditoría

Todos los eventos importantes deben registrarse en `AuditLog`:

- Logins exitosos y fallidos
- Creación/modificación/eliminación de recursos
- Cambios de configuración
- Accesos denegados
- Cambios de permisos

```typescript
async createAuditLog(data: {
  userId?: string;
  tenantUserId?: string;
  userType: 'admin' | 'tenant';
  userEmail: string;
  action: string;
  resource: string;
  resourceId?: string;
  changes?: any;
  ipAddress?: string;
  userAgent?: string;
}) {
  return this.prisma.auditLog.create({ data });
}
```

---

**Resumen:** Sistema de autenticación robusto con separación completa entre administradores del sistema y usuarios tenant, cada uno con su propio flujo de login, permisos y dashboards.
