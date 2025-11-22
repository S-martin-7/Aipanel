# AI_CONFIG_STRATEGY.md

## 1. Objetivo
Definir la estrategia para gestionar configuraciones de IA (proveedores, modelos, parámetros, rutas y flags) sin reiniciar el servidor. Permite que AIPanel se adapte rápidamente a cambios de la industria.

---

## 2. Principios
- **Configuración en BD**, no en código.
- **Recarga en caliente** con cache TTL.
- **AI Lab aislado** para pruebas.
- **Feature flags** para activar funciones.
- **Fallback automático** en caso de fallas.

---

## 3. Tipos de Configuración
- Proveedores (`ai_providers`)
- Modelos (`ai_models`)
- Perfiles (`ai_param_profiles`)
- Rutas (`ai_routes`)
- Flags (`feature_flags`)
- Config de agentes (`agents`)

---

## 4. Cache en Caliente
Se implementa un cache en memoria con TTL (30-60s). Permite que cambios en BD impacten sin reiniciar.

Se incorpora endpoint `/admin/config/invalidate-cache` para aplicación inmediata.

---

## 5. AI Lab vs Producción
**AI Lab:**
- Usa `tenant_id=INTERNAL_LAB`.
- Acepta modelos/proveedores no aprobados.
- Permite pruebas completas.

**Producción:**
- Solo usa `allowed_in_prod = true`.
- Solo usa modelos `STABLE` o `EXPERIMENTAL_OK`.

---

## 6. Versionado
### 6.1. Versionado en `agents`
Cada cambio crea una nueva `config_version` y guarda snapshot en `config_snapshot`.

### 6.2. Estados de modelos
- `EXPERIMENTAL`
- `STABLE`
- `DEPRECATED`
- `BLOCKED`

Esto guía el control de exposición.

---

## 7. Feature Flags
Controlan capacidades sin redeploy:
- `enable_realtime`
- `enable_anthropic`
- `enable_voice_input`

Se evalúan en runtime según scope (GLOBAL / TENANT / USER).

---

## 8. Manejo de Errores
- Modelos pueden tener `fallback_model_id`.
- Rutas pueden tener `fallback_route_id`.
- Falla → reintentos → fallback.

---

## 9. Observabilidad
Registros por:
- modelo
- proveedor
- tenant
- agente

Métricas de:
- latencia
- uso de tokens
- tasa de errores
- costo estimado

---

## 10. Resumen
El sistema permite:
- Activar y desactivar proveedores/modelos sin reiniciar.
- Probar todo en laboratorio sin arriesgar producción.
- Adaptarse a nuevos modelos y APIs con un solo cambio en BD.
- Controlar comportamiento con feature flags.
- Manejar errores con fallback.

Con esta estrategia, AIPanel es dinámico, estable y escalable sin necesidad de redeploy constante.

