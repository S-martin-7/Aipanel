# AI_PROVIDERS_AND_ROUTING.md

## 1. Objetivo
Definir una arquitectura flexible para gestionar proveedores de IA, modelos, parámetros y rutas dinámicas sin requerir cambios de código ni reinicios del servidor. Esto permite que AIPanel se adapte rápidamente a nuevas APIs, modelos o capacidades.

## 2. Componentes Clave
- **AI Provider Registry (BD):** mantiene información de proveedores y sus módulos de integración.
- **AI Model Registry (BD):** catálogo de modelos disponibles.
- **AI Parameter Profiles (BD):** perfiles de configuración de modelos.
- **AI Routes (BD):** determina qué proveedor/modelo usar por tenant, agente o modo.
- **AI Lab:** entorno aislado donde se prueban modelos y configuraciones antes de enviarlas a producción.
- **AI Engine:** núcleo que resuelve rutas, carga proveedores dynamically e invoca modelos.

---

## 3. Tablas Principales

### 3.1. `ai_providers`
Información del proveedor y el módulo Python encargado de su integración.

Campos clave:
- `handler_module`: ruta al módulo Python.
- `handler_class`: clase que implementa la interfaz.
- `config_json`: llaves API, endpoints, opciones.
- `allowed_in_prod`: controla visibilidad.

### 3.2. `ai_models`
Modelos disponibles por proveedor, capacidades, estado y costos.

### 3.3. `ai_param_profiles`
Parámetros reutilizables (temperatura, max_tokens, top_p, etc.).

### 3.4. `ai_routes`
Determina el camino a seguir para una request.

Incluye:
- `priority`
- `condition_json`
- `fallback_route_id`

### 3.5. `feature_flags`
Control granular de capacidades.

---

## 4. Plugins de Proveedor
Cada proveedor es un módulo `.py` que implementa la interfaz `AIProviderClientBase`.

Ejemplo:
```python
class OpenAIProviderClient(AIProviderClientBase):
    async def chat(...): ...
    async def realtime(...): ...
    async def embeddings(...): ...
```

Los módulos se cargan dinámicamente con `importlib`.

---

## 5. Lógica de Ruteo
El motor selecciona la ruta según:
- `tenant_id`
- `agent_id`
- `mode` (CHAT / REALTIME)
- condiciones (`condition_json`)
- prioridad

Si falla el modelo se usa el `fallback_route_id`.

---

## 6. AI Lab
El AI Lab permite:
- añadir proveedores
- añadir modelos
- escribir perfiles de parámetros
- probar chat / realtime
- habilitar modelos en producción

El Lab usa un tenant especial `INTERNAL_LAB`.

---

## 7. Flujo para Agregar Nuevo Proveedor
1. Crear `ai_providers` con módulo y clase.
2. Crear `ai_models` relacionados.
3. Crear perfiles en `ai_param_profiles`.
4. Probar en el Lab.
5. Marcar `allowed_in_prod = true`.
6. Crear rutas de ruteo.

---

## 8. Resumen
Este diseño garantiza:
- Extensibilidad.
- Cambios sin reinicios.
- Aislamiento total entre experimentos y producción.
- Capacidad de respuesta rápida a nuevos modelos o API.

