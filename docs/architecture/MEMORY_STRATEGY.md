# Estrategia de Memoria - Resúmenes Automáticos vs Vector Store

Análisis de alternativas para memoria de largo plazo y búsqueda de documentos.

## [X] Problema con Vector Stores Tradicionales

**Experiencia previa:**
- Implementación compleja y propensa a errores
- Pérdida de semanas en configuración
- Problemas de rendimiento
- Dependencia externa (Pinecone, Weaviate, etc.)
- Costos adicionales
- Debugging difícil

**Tecnologías problemáticas:**
- Pinecone (servicio externo, costos)
- Weaviate (configuración compleja)
- Milvus (recursos intensivos)
- Qdrant (curva de aprendizaje)
- pgvector (puede ser lento para grandes volúmenes)

---

## [OK] Solución Propuesta: Resúmenes Automáticos + PostgreSQL

### Concepto

En lugar de embeddings y búsqueda vectorial, usar **resúmenes jerárquicos** generados automáticamente por GPT y búsqueda de texto completo en PostgreSQL.

### Ventajas:

1. **Simplicidad** [OK]
   - Solo PostgreSQL (ya lo tienes)
   - Sin dependencias externas
   - Fácil de debuggear

2. **Velocidad de Implementación** [OK]
   - 1-2 días vs 2-3 semanas
   - Sin configuración compleja
   - Sin servidores adicionales

3. **Costo** [OK]
   - Sin servicios externos
   - Solo costo de tokens GPT para generar resúmenes
   - Resúmenes se generan 1 vez, se usan muchas veces

4. **Rendimiento Predecible** [OK]
   - PostgreSQL Full-Text Search es muy rápido
   - Índices GIN/GIST bien optimizados
   - No hay latencia de red a servicios externos

5. **Mejor Control** [OK]
   - Resúmenes legibles por humanos
   - Puedes editarlos manualmente si es necesario
   - Fácil auditar qué información se está usando

---

## [#] Arquitectura de Resúmenes Jerárquicos

### Modelo de Datos

```prisma
// Documento original subido por el usuario
model Document {
  id              String   @id @default(cuid())
  tenantId        String
  agentId         String?
  name            String
  type            String   // 'pdf', 'url', 'text'
  originalUrl     String?
  s3Key           String?  // Si está en S3
  content         String   @db.Text  // Contenido extraído
  contentHash     String   // SHA256 para detectar duplicados
  size            Int      // Tamaño en bytes

  // Metadatos
  metadata        Json?    // { author, date, etc }

  // Relaciones
  chunks          DocumentChunk[]
  summaries       DocumentSummary[]

  createdAt       DateTime @default(now())
  updatedAt       DateTime @updatedAt

  @@map("documents")
  @@index([tenantId, agentId])
  @@index([contentHash])
}

// Chunks del documento (división inteligente)
model DocumentChunk {
  id              String   @id @default(cuid())
  documentId      String
  chunkIndex      Int      // Orden del chunk
  content         String   @db.Text
  wordCount       Int

  // Para búsqueda de texto completo
  searchVector    Unsupported("tsvector")?

  // Relaciones
  document        Document @relation(fields: [documentId], references: [id], onDelete: Cascade)
  summaries       ChunkSummary[]

  createdAt       DateTime @default(now())

  @@map("document_chunks")
  @@index([documentId, chunkIndex])
  @@index([searchVector], type: Gin)
}

// Resumen del chunk (generado por GPT)
model ChunkSummary {
  id              String   @id @default(cuid())
  chunkId         String
  summary         String   @db.Text  // Resumen del chunk
  keywords        String[]          // Keywords extraídas
  topics          String[]          // Tópicos identificados

  // Metadatos
  model           String   // "gpt-4o-mini" o el que se usó
  tokensUsed      Int

  // Para búsqueda
  searchVector    Unsupported("tsvector")?

  // Relaciones
  chunk           DocumentChunk @relation(fields: [chunkId], references: [id], onDelete: Cascade)

  createdAt       DateTime @default(now())

  @@map("chunk_summaries")
  @@unique([chunkId])
  @@index([keywords])
  @@index([topics])
  @@index([searchVector], type: Gin)
}

// Resumen de documento completo (rollup de chunks)
model DocumentSummary {
  id              String   @id @default(cuid())
  documentId      String
  level           Int      @default(1)  // Nivel de abstracción
  summary         String   @db.Text
  keyPoints       String[] // Puntos clave
  keywords        String[]
  topics          String[]

  // Metadatos
  model           String
  tokensUsed      Int

  // Para búsqueda
  searchVector    Unsupported("tsvector")?

  // Relaciones
  document        Document @relation(fields: [documentId], references: [id], onDelete: Cascade)

  createdAt       DateTime @default(now())

  @@map("document_summaries")
  @@index([documentId, level])
  @@index([keywords])
  @@index([topics])
  @@index([searchVector], type: Gin)
}
```

---

## [?] Proceso de Ingesta de Documentos

### 1. Upload de Documento

```python
# app/services/document_processor.py

class DocumentProcessor:
    def __init__(self, openai_client, s3_client):
        self.openai = openai_client
        self.s3 = s3_client

    async def process_document(
        self,
        file: UploadFile,
        tenant_id: str,
        agent_id: str = None
    ) -> Document:
        """Procesar documento completo"""

        # 1. Extraer contenido
        content = await self.extract_content(file)

        # 2. Guardar original en S3
        s3_key = f"{tenant_id}/documents/{file.filename}"
        await self.s3.upload(file, s3_key)

        # 3. Crear documento en DB
        document = await db.documents.create({
            "tenant_id": tenant_id,
            "agent_id": agent_id,
            "name": file.filename,
            "type": self.detect_type(file),
            "content": content,
            "content_hash": hashlib.sha256(content.encode()).hexdigest(),
            "size": len(content),
            "s3_key": s3_key
        })

        # 4. Dividir en chunks (async task)
        await self.chunk_and_summarize(document.id)

        return document
```

### 2. Chunking Inteligente

```python
async def chunk_and_summarize(self, document_id: str):
    """Dividir documento en chunks y generar resúmenes"""

    document = await db.documents.get(document_id)

    # Chunking basado en párrafos/secciones (no arbitrario)
    chunks = self.intelligent_chunking(
        content=document.content,
        max_chunk_size=2000,  # ~500 palabras
        overlap=200  # Overlap entre chunks
    )

    # Crear chunks en DB
    for i, chunk_content in enumerate(chunks):
        chunk = await db.chunks.create({
            "document_id": document_id,
            "chunk_index": i,
            "content": chunk_content,
            "word_count": len(chunk_content.split())
        })

        # Generar resumen del chunk (async)
        await self.summarize_chunk(chunk.id)

    # Generar resumen del documento completo
    await self.summarize_document(document_id)

def intelligent_chunking(
    self,
    content: str,
    max_chunk_size: int = 2000,
    overlap: int = 200
) -> List[str]:
    """División inteligente por párrafos/secciones"""

    # Dividir por párrafos primero
    paragraphs = content.split('\n\n')

    chunks = []
    current_chunk = []
    current_size = 0

    for para in paragraphs:
        para_size = len(para)

        if current_size + para_size > max_chunk_size and current_chunk:
            # Guardar chunk actual
            chunks.append('\n\n'.join(current_chunk))

            # Empezar nuevo chunk con overlap
            if len(current_chunk) > 1:
                current_chunk = [current_chunk[-1]]  # Último párrafo como overlap
                current_size = len(current_chunk[0])
            else:
                current_chunk = []
                current_size = 0

        current_chunk.append(para)
        current_size += para_size

    # Último chunk
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))

    return chunks
```

### 3. Generación de Resúmenes

```python
async def summarize_chunk(self, chunk_id: str):
    """Generar resumen de un chunk usando GPT"""

    chunk = await db.chunks.get(chunk_id)

    # Prompt optimizado
    response = await self.openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """Eres un asistente que resume documentos de forma concisa.

Tareas:
1. Resume el texto en 2-3 oraciones
2. Extrae las keywords más importantes (máximo 10)
3. Identifica los tópicos principales (máximo 5)

Formato de respuesta (JSON):
{
  "summary": "Resumen conciso del texto...",
  "keywords": ["keyword1", "keyword2", ...],
  "topics": ["topic1", "topic2", ...]
}"""
            },
            {
                "role": "user",
                "content": f"Resume este texto:\n\n{chunk.content}"
            }
        ],
        response_format={"type": "json_object"},
        temperature=0.3
    )

    result = json.loads(response.choices[0].message.content)

    # Guardar resumen en DB
    await db.chunk_summaries.create({
        "chunk_id": chunk_id,
        "summary": result["summary"],
        "keywords": result["keywords"],
        "topics": result["topics"],
        "model": "gpt-4o-mini",
        "tokens_used": response.usage.total_tokens
    })

async def summarize_document(self, document_id: str):
    """Generar resumen del documento completo (rollup)"""

    # Obtener todos los resúmenes de chunks
    chunk_summaries = await db.chunk_summaries.find({
        "chunk.document_id": document_id
    })

    # Combinar resúmenes de chunks
    combined_summaries = "\n\n".join([cs.summary for cs in chunk_summaries])

    # Generar resumen de nivel superior
    response = await self.openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """Resume estos resúmenes en un resumen ejecutivo.

Formato JSON:
{
  "summary": "Resumen ejecutivo del documento completo...",
  "key_points": ["punto1", "punto2", ...],
  "keywords": ["keyword1", ...],
  "topics": ["topic1", ...]
}"""
            },
            {
                "role": "user",
                "content": f"Resúmenes de secciones:\n\n{combined_summaries}"
            }
        ],
        response_format={"type": "json_object"},
        temperature=0.3
    )

    result = json.loads(response.choices[0].message.content)

    # Guardar resumen del documento
    await db.document_summaries.create({
        "document_id": document_id,
        "level": 1,
        "summary": result["summary"],
        "key_points": result["key_points"],
        "keywords": result["keywords"],
        "topics": result["topics"],
        "model": "gpt-4o-mini",
        "tokens_used": response.usage.total_tokens
    })
```

---

## [?] Búsqueda y Recuperación

### Full-Text Search en PostgreSQL

```sql
-- Crear índice de texto completo
CREATE INDEX idx_chunks_search ON document_chunks
USING GIN (to_tsvector('spanish', content));

CREATE INDEX idx_summaries_search ON chunk_summaries
USING GIN (to_tsvector('spanish', summary));

CREATE INDEX idx_doc_summaries_search ON document_summaries
USING GIN (to_tsvector('spanish', summary));
```

### Servicio de Búsqueda

```python
# app/services/search_service.py

class SearchService:
    async def search_documents(
        self,
        tenant_id: str,
        query: str,
        agent_id: str = None,
        limit: int = 10
    ) -> List[SearchResult]:
        """Buscar documentos relevantes"""

        # Búsqueda híbrida: keywords + full-text search
        results = []

        # 1. Buscar en resúmenes de documentos (nivel alto)
        doc_summaries = await db.raw("""
            SELECT
                ds.*,
                d.name as document_name,
                ts_rank(
                    to_tsvector('spanish', ds.summary),
                    plainto_tsquery('spanish', $1)
                ) as rank
            FROM document_summaries ds
            JOIN documents d ON d.id = ds.document_id
            WHERE
                d.tenant_id = $2
                AND to_tsvector('spanish', ds.summary) @@ plainto_tsquery('spanish', $1)
            ORDER BY rank DESC
            LIMIT $3
        """, [query, tenant_id, limit])

        # 2. Buscar en keywords/topics
        topic_matches = await db.document_summaries.find({
            "document.tenant_id": tenant_id,
            "keywords": {"$in": self.extract_keywords(query)}
        })

        # 3. Si no hay suficientes resultados, buscar en chunks
        if len(doc_summaries) < 3:
            chunk_matches = await db.raw("""
                SELECT
                    cs.*,
                    c.content as chunk_content,
                    d.name as document_name,
                    ts_rank(
                        to_tsvector('spanish', cs.summary),
                        plainto_tsquery('spanish', $1)
                    ) as rank
                FROM chunk_summaries cs
                JOIN document_chunks c ON c.id = cs.chunk_id
                JOIN documents d ON d.id = c.document_id
                WHERE
                    d.tenant_id = $2
                    AND to_tsvector('spanish', cs.summary) @@ plainto_tsquery('spanish', $1)
                ORDER BY rank DESC
                LIMIT $3
            """, [query, tenant_id, limit])

            results.extend(chunk_matches)

        return results

    def extract_keywords(self, query: str) -> List[str]:
        """Extraer keywords de la query"""
        # Simple: dividir por espacios y filtrar stopwords
        stopwords = {'el', 'la', 'de', 'en', 'y', 'a', 'que', 'es', 'por', 'un', 'una'}
        words = query.lower().split()
        return [w for w in words if w not in stopwords and len(w) > 3]
```

---

## [?] Integración con Chat (RAG Simplificado)

```python
# app/services/chat_service.py

class ChatService:
    async def chat_with_agent(
        self,
        agent_id: str,
        message: str,
        conversation_id: str = None
    ) -> ChatResponse:
        """Chat con agente usando memoria de documentos"""

        agent = await db.agents.get(agent_id)

        # 1. Buscar documentos relevantes
        relevant_docs = await search_service.search_documents(
            tenant_id=agent.tenant_id,
            query=message,
            agent_id=agent_id,
            limit=5
        )

        # 2. Construir contexto desde resúmenes
        context = self.build_context(relevant_docs)

        # 3. Obtener historial de conversación
        history = await self.get_conversation_history(conversation_id)

        # 4. Construir prompt con contexto
        messages = [
            {
                "role": "system",
                "content": f"""{agent.system_prompt}

# Contexto de documentos relevantes:

{context}

Usa esta información para responder preguntas del usuario. Si la información no está en el contexto, indícalo claramente."""
            }
        ]

        # Agregar historial
        messages.extend(history)

        # Agregar mensaje del usuario
        messages.append({"role": "user", "content": message})

        # 5. Llamar a OpenAI
        response = await openai.chat.completions.create(
            model=agent.model,
            messages=messages,
            temperature=agent.temperature,
            max_tokens=agent.max_tokens
        )

        # 6. Guardar en conversación
        await self.save_message(conversation_id, message, response)

        # 7. Track tokens
        await token_tracker.track_usage(
            tenant_id=agent.tenant_id,
            agent_id=agent_id,
            model=agent.model,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens
        )

        return ChatResponse(
            message=response.choices[0].message.content,
            sources=[d.document_name for d in relevant_docs]
        )

    def build_context(self, search_results: List[SearchResult]) -> str:
        """Construir contexto legible desde resultados"""

        context_parts = []

        for i, result in enumerate(search_results, 1):
            context_parts.append(f"""
## Documento {i}: {result.document_name}

{result.summary}

**Keywords:** {', '.join(result.keywords)}
**Topics:** {', '.join(result.topics)}
""")

        return "\n\n".join(context_parts)
```

---

## [=] Comparación: Resúmenes vs Vector Store

| Aspecto | Vector Store | Resúmenes Automáticos |
|---------|--------------|----------------------|
| **Complejidad** | Alta (embeddings, índices HNSW) | Baja (SQL + GPT) |
| **Tiempo de implementación** | 2-3 semanas | 2-3 días |
| **Dependencias** | Pinecone/Weaviate/etc | Solo PostgreSQL |
| **Costo recurrente** | $$ (servicio externo) | $ (solo storage) |
| **Debugging** | Difícil (caja negra) | Fácil (resúmenes legibles) |
| **Precisión** | Alta (semántica pura) | Alta (contexto + keywords) |
| **Velocidad** | Muy rápida | Rápida |
| **Mantenimiento** | Medio-Alto | Bajo |
| **Escalabilidad** | Excelente | Buena (hasta 1M docs) |
| **Control** | Limitado | Total |

---

## [+] Recomendación Final

### Para AIPanel: **Usar Resúmenes Automáticos**

**Justificación:**

1. **MVP más rápido** [OK]
   - Implementar en días, no semanas
   - Menos riesgo de bloqueo técnico

2. **Suficientemente bueno** [OK]
   - Para 90% de casos de uso es suficiente
   - Búsqueda por keywords + tópicos + full-text es muy efectiva

3. **Más barato** [OK]
   - Sin costos recurrentes de servicios externos
   - Generas resúmenes 1 vez, los usas miles de veces

4. **Más confiable** [OK]
   - Menos cosas que pueden fallar
   - Resúmenes son auditables y editables

5. **Migración futura posible** [OK]
   - Si necesitas vector store más adelante, puedes agregarlo
   - Los resúmenes seguirán siendo útiles como fallback

---

## [*] Plan de Implementación

### Semana 1: Backend
- [x] Modelos de datos (Document, Chunk, Summary)
- [x] Servicio de procesamiento de documentos
- [x] Chunking inteligente
- [x] Generación de resúmenes con GPT
- [x] Índices de búsqueda full-text

### Semana 2: Búsqueda + Chat
- [x] Servicio de búsqueda híbrida
- [x] Integración con chat (RAG simplificado)
- [x] Endpoints REST
- [x] Testing

### Semana 3: Frontend
- [x] UI de upload de documentos
- [x] Visor de documentos y resúmenes
- [x] Búsqueda de documentos
- [x] Integración con chat

**Total: 3 semanas vs 6+ semanas con vector store tradicional**

---

## [i] Optimizaciones Futuras (Opcional)

Si más adelante necesitas mejor rendimiento:

1. **Hybrid Search:**
   - Agregar pgvector para embeddings
   - Combinar búsqueda semántica + resúmenes
   - Lo mejor de ambos mundos

2. **Caché de Resúmenes:**
   - Redis para resúmenes frecuentes
   - Reduce latencia de búsqueda

3. **Resúmenes Multi-nivel:**
   - Nivel 1: Resumen ejecutivo (100 palabras)
   - Nivel 2: Resumen medio (500 palabras)
   - Nivel 3: Resumen detallado (1000 palabras)
   - Usar según contexto

4. **Auto-mejora:**
   - Analizar qué documentos se usan más
   - Re-generar resúmenes con mejor prompt
   - A/B testing de prompts de resumen

Pero para MVP: **KISS (Keep It Simple, Stupid)** [OK]
