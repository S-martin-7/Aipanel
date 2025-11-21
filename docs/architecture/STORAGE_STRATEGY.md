# Estrategia de Almacenamiento: S3 vs Base de Datos

## Resumen Ejecutivo

AIPanel utiliza una **estrategia hibrida** de almacenamiento:
- **S3 (MinIO)**: Para archivos binarios (PDFs, imagenes, audio)
- **PostgreSQL**: Para texto, chunks, resumenes y metadatos

Esta estrategia optimiza costos y rendimiento, aprovechando las fortalezas de cada sistema.

## Problema a Resolver

La memoria en AIPanel se mide en **GB por tenant**, no en tiempo. Cada plan tiene cuotas:
- Plan Basico: 1 GB
- Plan Pro: 5 GB
- Plan Enterprise: 20+ GB

Necesitamos:
1. Almacenar documentos de forma eficiente
2. Buscar rapidamente en el contenido
3. Calcular el uso de memoria por tenant
4. Aplicar politicas de retencion
5. Optimizar costos de almacenamiento

## Decision: Estrategia Hibrida

### S3 (MinIO) para Archivos Binarios

**Que se almacena en S3:**
- Archivos PDF originales
- Imagenes (PNG, JPG, GIF)
- Archivos de audio (MP3, WAV, OGG)
- Videos (MP4, AVI)
- Cualquier archivo binario subido por usuarios

**Por que S3:**
- Costo bajo: ~$0.023 USD por GB/mes (MinIO self-hosted aun mas barato)
- Escalabilidad ilimitada
- Durabilidad alta (99.999999999%)
- Acceso via URLs firmadas (pre-signed URLs)
- Lifecycle policies (mover a storage frio automaticamente)
- No consume recursos de base de datos

**Estructura de paths en S3:**
```
s3://aipanel-documents/
  ├── tenant_<tenant_id>/
  │   ├── documents/
  │   │   ├── <document_id>.pdf
  │   │   ├── <document_id>.png
  │   ├── agents/
  │   │   ├── <agent_id>/
  │   │   │   ├── <file_id>.pdf
  │   ├── exports/
  │       ├── <export_id>.zip
```

### PostgreSQL para Texto y Resumenes

**Que se almacena en BD:**
- Texto extraido de documentos
- Chunks de texto (fragmentos)
- Resumenes automaticos (por chunk y por documento)
- Metadatos (nombre, tamaño, fecha, tenant_id)
- Keywords y tags
- Indices full-text search

**Por que PostgreSQL:**
- Busqueda full-text rapida (GIN indexes)
- Queries complejas con filtros
- Transacciones ACID
- Relaciones con agents, tenants
- Agregaciones (calcular uso de memoria)
- Row-Level Security (aislamiento por tenant)

**Esquema de tablas:**
```sql
-- Tabla de documentos (metadatos)
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    agent_id UUID,
    filename VARCHAR(255),
    content_type VARCHAR(50),
    file_size_bytes BIGINT,  -- Tamaño del archivo original
    s3_path VARCHAR(500),    -- Path en S3
    uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    status VARCHAR(20),      -- 'pending', 'processing', 'completed', 'failed'
    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

-- Tabla de chunks (fragmentos de texto)
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    chunk_index INT,
    content TEXT,            -- Texto del chunk
    content_size_bytes INT,  -- Tamaño en bytes
    summary TEXT,            -- Resumen del chunk
    summary_size_bytes INT,
    keywords TEXT[],
    page_number INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- Tabla de resumenes de documentos completos
CREATE TABLE document_summaries (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    summary TEXT,            -- Resumen del documento completo
    summary_size_bytes INT,
    keywords TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- Indices para busqueda full-text
CREATE INDEX idx_chunks_content_fts ON document_chunks USING GIN(to_tsvector('spanish', content));
CREATE INDEX idx_chunks_summary_fts ON document_chunks USING GIN(to_tsvector('spanish', summary));
CREATE INDEX idx_summaries_fts ON document_summaries USING GIN(to_tsvector('spanish', summary));
```

## Flujo de Procesamiento de Documentos

### 1. Upload

```
Usuario sube PDF (50 MB)
    ↓
API recibe archivo
    ↓
Se sube a S3 (async)
    ↓
Se crea registro en documents (status='pending')
    ↓
Se lanza tarea Celery para procesamiento
```

### 2. Procesamiento

```
Celery worker recibe tarea
    ↓
Descarga PDF desde S3
    ↓
Extrae texto (PyPDF2 o pdfplumber)
    ↓
Si es imagen/escaneado: OCR con pytesseract
    ↓
Divide en chunks (500 palabras por chunk)
    ↓
Para cada chunk:
    - Guarda texto en document_chunks
    - Genera resumen con GPT-4o-mini
    - Extrae keywords
    - Guarda resumen en document_chunks
    ↓
Genera resumen del documento completo (rollup de summaries)
    ↓
Guarda en document_summaries
    ↓
Actualiza documents (status='completed')
    ↓
Actualiza memoria usada por tenant
```

### 3. Busqueda (RAG)

```
Usuario pregunta: "Que dice el contrato sobre clausulas de terminacion?"
    ↓
Sistema busca en:
    1. document_summaries (resumen completo)
    2. document_chunks.summary (resumenes de chunks)
    3. document_chunks.content (texto completo)
    ↓
Usa full-text search + ranking:
    SELECT *, ts_rank(to_tsvector('spanish', content), query) as rank
    FROM document_chunks
    WHERE tenant_id = ? AND to_tsvector('spanish', content) @@ query
    ORDER BY rank DESC
    LIMIT 5
    ↓
Devuelve top 5 chunks mas relevantes
    ↓
Construye prompt con contexto
    ↓
Envia a GPT-4o para respuesta final
```

## Calculo de Memoria por Tenant

La memoria se calcula sumando:

1. **Archivos originales en S3** (peso completo)
2. **Texto en BD** (chunks.content + summaries.summary)

```sql
-- Query para calcular uso de memoria por tenant
SELECT
    t.id as tenant_id,
    t.name,
    -- Archivos en S3
    COALESCE(SUM(d.file_size_bytes), 0) as s3_bytes,
    -- Texto en BD (chunks)
    COALESCE(SUM(dc.content_size_bytes + dc.summary_size_bytes), 0) as chunks_bytes,
    -- Resumenes de documentos
    COALESCE(SUM(ds.summary_size_bytes), 0) as summaries_bytes,
    -- Total
    COALESCE(
        SUM(d.file_size_bytes) +
        SUM(dc.content_size_bytes + dc.summary_size_bytes) +
        SUM(ds.summary_size_bytes),
        0
    ) as total_bytes,
    -- Convertir a GB
    ROUND(
        COALESCE(
            SUM(d.file_size_bytes) +
            SUM(dc.content_size_bytes + dc.summary_size_bytes) +
            SUM(ds.summary_size_bytes),
            0
        ) / 1024.0 / 1024.0 / 1024.0,
        2
    ) as total_gb
FROM tenants t
LEFT JOIN documents d ON d.tenant_id = t.id
LEFT JOIN document_chunks dc ON dc.tenant_id = t.id
LEFT JOIN document_summaries ds ON ds.tenant_id = t.id
WHERE t.id = ?
GROUP BY t.id, t.name;
```

## Politicas de Retencion

Cada plan tiene una politica de retencion:

| Plan | Retencion | Accion al Expirar |
|---|---|---|
| Basico | 3 meses | Borrar documento + chunks + summaries |
| Pro | 12 meses | Mover a S3 Glacier (storage frio) |
| Enterprise | Ilimitado | No se borra |

### Implementacion con Celery

```python
# Tarea que se ejecuta diariamente
@celery_app.task
def cleanup_expired_documents():
    """Limpia documentos expirados segun plan."""

    # Obtener documentos expirados
    expired_docs = db.query(Document).join(Tenant).filter(
        # Plan Basico: > 3 meses
        or_(
            and_(
                Tenant.plan == 'basico',
                Document.uploaded_at < datetime.now() - timedelta(days=90)
            ),
            # Plan Pro: > 12 meses
            and_(
                Tenant.plan == 'pro',
                Document.uploaded_at < datetime.now() - timedelta(days=365)
            )
        )
    ).all()

    for doc in expired_docs:
        tenant = doc.tenant

        if tenant.plan == 'basico':
            # Borrar completamente
            s3_client.delete_object(Bucket='aipanel-documents', Key=doc.s3_path)
            db.delete(doc)  # Cascade borra chunks y summaries

        elif tenant.plan == 'pro':
            # Mover a Glacier (storage frio)
            s3_client.copy_object(
                Bucket='aipanel-documents-glacier',
                Key=doc.s3_path,
                CopySource={'Bucket': 'aipanel-documents', 'Key': doc.s3_path}
            )
            s3_client.delete_object(Bucket='aipanel-documents', Key=doc.s3_path)
            doc.status = 'archived'
            db.commit()

    logger.info(f"Cleaned up {len(expired_docs)} expired documents")
```

## Optimizacion de Costos

### Costos Estimados

**S3 (MinIO self-hosted):**
- 1 TB storage: ~$0 (disco duro local)
- Ancho de banda: ~$0 (LAN local)

**PostgreSQL:**
- 1 GB de texto: ~$0.10-0.20 USD/mes (VPS incluido)
- Indices: ~20% overhead adicional

**Total estimado:**
- 100 GB de archivos en S3: ~$0 (self-hosted)
- 5 GB de texto en BD: ~$1 USD/mes
- **Costo por GB de memoria: ~$0.20 USD/mes**

### Comparacion: Todo en BD vs Hibrido

| Escenario | Storage | Costo Mensual | Rendimiento | Escalabilidad |
|---|---|---|---|---|
| **Todo en BD** | 100 GB | $10-20 | Lento (queries pesadas) | Limitado |
| **Hibrido (S3+BD)** | 100 GB S3 + 5 GB BD | $1-2 | Rapido | Ilimitado |

**Ahorro con estrategia hibrida: 80-90%**

## Ventajas de la Estrategia Hibrida

1. **Costos Optimizados**: S3 es 10x mas barato que BD para archivos binarios
2. **Rendimiento**: Busquedas full-text en BD son rapidas, S3 solo para download
3. **Escalabilidad**: S3 escala infinitamente sin afectar BD
4. **Simplicidad**: No necesitamos vector stores (Pinecone, Weaviate, etc.)
5. **Debuggeable**: Los resumenes son legibles, facil de debuggear
6. **Backup**: S3 tiene replicacion automatica, BD tiene backups diarios

## Desventajas de Vector Stores (por que NO los usamos)

El usuario reporto: "Vector store no funciono en proyecto anterior, perdi semanas"

**Problemas con vector stores:**
1. **Complejidad**: Requiere embeddings, indices vectoriales, tuning
2. **Dependencias**: Servicios externos (Pinecone, Weaviate) o self-hosted (Qdrant)
3. **Costo**: Pinecone cobra por indice + queries
4. **Debugging**: Embeddings son vectores de 1536 dimensiones, no legibles
5. **Mantenimiento**: Requiere re-indexing periodico
6. **Latencia**: Queries pueden ser lentas con millones de vectores

**Nuestra solucion: Resumenes automaticos**
1. **Simple**: Texto → Resumen (GPT-4o-mini)
2. **Sin dependencias**: Solo PostgreSQL
3. **Barato**: Resumenes se generan una vez, busqueda es gratis
4. **Debuggeable**: Resumenes son legibles, facil de entender que encontro
5. **Rapido**: Full-text search en PostgreSQL es muy rapido (<50ms)

## Implementacion Tecnica

### Configuracion de S3 (MinIO)

```python
# backend/app/core/storage.py

import boto3
from botocore.client import Config

s3_client = boto3.client(
    's3',
    endpoint_url=settings.S3_ENDPOINT_URL,  # http://localhost:9000 para MinIO
    aws_access_key_id=settings.S3_ACCESS_KEY,
    aws_secret_access_key=settings.S3_SECRET_KEY,
    config=Config(signature_version='s3v4'),
    region_name='us-east-1'
)

def upload_file_to_s3(file_path: str, tenant_id: str, document_id: str) -> str:
    """Sube archivo a S3 y retorna path."""

    s3_path = f"tenant_{tenant_id}/documents/{document_id}.pdf"

    s3_client.upload_file(
        file_path,
        settings.S3_BUCKET_NAME,
        s3_path,
        ExtraArgs={'ContentType': 'application/pdf'}
    )

    return s3_path

def get_presigned_url(s3_path: str, expires_in: int = 3600) -> str:
    """Genera URL firmada para download."""

    url = s3_client.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': settings.S3_BUCKET_NAME,
            'Key': s3_path
        },
        ExpiresIn=expires_in
    )

    return url
```

### Servicio de Procesamiento

```python
# backend/app/modules/documents/service.py

from app.core.storage import upload_file_to_s3
from app.modules.documents.tasks import process_document_task

async def upload_document(
    file: UploadFile,
    tenant_id: str,
    agent_id: str
) -> Document:
    """Sube documento y lanza procesamiento."""

    # 1. Crear registro en BD
    document = Document(
        id=uuid4(),
        tenant_id=tenant_id,
        agent_id=agent_id,
        filename=file.filename,
        content_type=file.content_type,
        file_size_bytes=file.size,
        status='pending'
    )
    db.add(document)
    await db.commit()

    # 2. Guardar archivo temporal
    temp_path = f"/tmp/{document.id}"
    with open(temp_path, 'wb') as f:
        f.write(await file.read())

    # 3. Subir a S3
    s3_path = upload_file_to_s3(temp_path, tenant_id, str(document.id))
    document.s3_path = s3_path
    await db.commit()

    # 4. Lanzar tarea de procesamiento (async)
    process_document_task.delay(str(document.id))

    return document
```

## Conclusiones

La estrategia hibrida S3 + PostgreSQL es:
- **Simple**: Sin dependencias complejas
- **Economica**: Ahorro de 80-90% vs todo en BD
- **Escalable**: S3 escala infinitamente
- **Rapida**: Full-text search en BD es muy rapido
- **Debuggeable**: Resumenes legibles

Esta estrategia permite cumplir con los planes comerciales (1 GB, 5 GB, 20+ GB) sin explotar costos ni complejidad.
