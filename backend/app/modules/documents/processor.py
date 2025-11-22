"""
Documents Module - Text Processor

Handles document parsing, chunking, and summary generation.
Uses simplified RAG approach with summaries instead of vector embeddings.
"""

import re
from typing import Optional
from dataclasses import dataclass

from app.integrations import AIEngine
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Constants
DEFAULT_CHUNK_SIZE = 1000  # tokens (approximate)
DEFAULT_CHUNK_OVERLAP = 100
MAX_SUMMARY_TOKENS = 150


@dataclass
class TextChunk:
    """A chunk of processed text."""
    index: int
    content: str
    token_count: int
    start_char: int
    end_char: int


@dataclass
class ProcessedDocument:
    """Result of document processing."""
    chunks: list[TextChunk]
    total_tokens: int
    summary: Optional[str] = None


class TextProcessor:
    """
    Processes documents into chunks with summaries.

    Features:
    - Smart text chunking by paragraphs/sentences
    - Token counting (approximate)
    - Summary generation per chunk
    - Document-level summary
    """

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        ai_engine: Optional[AIEngine] = None,
    ):
        """
        Initialize text processor.

        Args:
            chunk_size: Target tokens per chunk
            chunk_overlap: Overlap between chunks
            ai_engine: Optional AI engine for summaries
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.ai_engine = ai_engine

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Uses simple word-based approximation (1 token ≈ 0.75 words).
        """
        words = len(text.split())
        return int(words / 0.75)

    def extract_text_from_pdf(self, content: bytes) -> str:
        """
        Extract text from PDF bytes.

        Uses pypdf if available, otherwise returns empty.
        """
        try:
            from pypdf import PdfReader
            from io import BytesIO

            reader = PdfReader(BytesIO(content))
            text_parts = []

            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            return "\n\n".join(text_parts)
        except ImportError:
            logger.warning("pypdf not installed, PDF extraction unavailable")
            return ""
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            return ""

    def extract_text(self, content: bytes, file_type: str) -> str:
        """
        Extract text from document bytes.

        Args:
            content: Raw file bytes
            file_type: File extension (pdf, txt, md, html)

        Returns:
            Extracted text content
        """
        file_type = file_type.lower().strip(".")

        if file_type == "pdf":
            return self.extract_text_from_pdf(content)
        elif file_type in ("txt", "md"):
            return content.decode("utf-8", errors="ignore")
        elif file_type == "html":
            return self._strip_html(content.decode("utf-8", errors="ignore"))
        else:
            # Try as plain text
            return content.decode("utf-8", errors="ignore")

    def _strip_html(self, html: str) -> str:
        """Remove HTML tags from text."""
        # Remove script and style elements
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
        # Remove tags
        html = re.sub(r"<[^>]+>", " ", html)
        # Clean whitespace
        html = re.sub(r"\s+", " ", html)
        return html.strip()

    def chunk_text(self, text: str) -> list[TextChunk]:
        """
        Split text into chunks.

        Strategy:
        1. Split by paragraphs first
        2. If paragraph too large, split by sentences
        3. Combine small paragraphs up to chunk_size
        """
        chunks: list[TextChunk] = []
        paragraphs = self._split_paragraphs(text)

        current_content = ""
        current_start = 0
        chunk_index = 0

        for para in paragraphs:
            para_tokens = self.estimate_tokens(para)

            # If paragraph alone exceeds chunk size, split it
            if para_tokens > self.chunk_size:
                # Save current chunk if exists
                if current_content:
                    chunks.append(TextChunk(
                        index=chunk_index,
                        content=current_content.strip(),
                        token_count=self.estimate_tokens(current_content),
                        start_char=current_start,
                        end_char=current_start + len(current_content),
                    ))
                    chunk_index += 1
                    current_content = ""

                # Split large paragraph by sentences
                sentences = self._split_sentences(para)
                for sent in sentences:
                    sent_tokens = self.estimate_tokens(sent)
                    combined_tokens = self.estimate_tokens(current_content + " " + sent)

                    if combined_tokens > self.chunk_size and current_content:
                        chunks.append(TextChunk(
                            index=chunk_index,
                            content=current_content.strip(),
                            token_count=self.estimate_tokens(current_content),
                            start_char=current_start,
                            end_char=current_start + len(current_content),
                        ))
                        chunk_index += 1
                        # Keep overlap
                        overlap_text = current_content[-self.chunk_overlap * 4:] if len(current_content) > self.chunk_overlap * 4 else ""
                        current_content = overlap_text + " " + sent
                        current_start = current_start + len(current_content) - len(overlap_text) - len(sent) - 1
                    else:
                        current_content += " " + sent

            else:
                combined_tokens = self.estimate_tokens(current_content + "\n\n" + para)

                if combined_tokens > self.chunk_size and current_content:
                    chunks.append(TextChunk(
                        index=chunk_index,
                        content=current_content.strip(),
                        token_count=self.estimate_tokens(current_content),
                        start_char=current_start,
                        end_char=current_start + len(current_content),
                    ))
                    chunk_index += 1
                    current_content = para
                    current_start = current_start + len(current_content)
                else:
                    if current_content:
                        current_content += "\n\n" + para
                    else:
                        current_content = para

        # Don't forget last chunk
        if current_content.strip():
            chunks.append(TextChunk(
                index=chunk_index,
                content=current_content.strip(),
                token_count=self.estimate_tokens(current_content),
                start_char=current_start,
                end_char=current_start + len(current_content),
            ))

        return chunks

    def _split_paragraphs(self, text: str) -> list[str]:
        """Split text into paragraphs."""
        # Split by double newlines or multiple newlines
        paragraphs = re.split(r"\n\s*\n", text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    async def generate_chunk_summary(
        self,
        chunk: TextChunk,
        tenant_id: str,
        agent_id: str,
    ) -> str:
        """
        Generate summary for a chunk using AI.

        Args:
            chunk: Text chunk to summarize
            tenant_id: Tenant ID for AI routing
            agent_id: Agent ID for AI routing

        Returns:
            Summary text
        """
        if not self.ai_engine:
            # Fallback: first 200 chars
            return chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content

        try:
            from app.integrations import Message

            messages = [
                Message(
                    role="system",
                    content="You are a summarization assistant. Provide a concise summary of the text in 1-2 sentences. Focus on key information."
                ),
                Message(
                    role="user",
                    content=f"Summarize this text:\n\n{chunk.content}"
                ),
            ]

            response = await self.ai_engine.chat_completion(
                messages=messages,
                tenant_id=tenant_id,
                agent_id=agent_id,
                max_tokens=MAX_SUMMARY_TOKENS,
            )

            return response.content
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content

    async def generate_document_summary(
        self,
        chunks: list[TextChunk],
        tenant_id: str,
        agent_id: str,
    ) -> str:
        """
        Generate overall document summary.

        Uses first few chunks to create document summary.
        """
        if not self.ai_engine:
            # Fallback: combine first chunks
            combined = " ".join(c.content[:200] for c in chunks[:3])
            return combined[:500]

        try:
            from app.integrations import Message

            # Use first chunks for context
            context = "\n\n".join(c.content for c in chunks[:5])[:3000]

            messages = [
                Message(
                    role="system",
                    content="You are a summarization assistant. Provide a comprehensive summary of the document in 3-5 sentences."
                ),
                Message(
                    role="user",
                    content=f"Summarize this document:\n\n{context}"
                ),
            ]

            response = await self.ai_engine.chat_completion(
                messages=messages,
                tenant_id=tenant_id,
                agent_id=agent_id,
                max_tokens=300,
            )

            return response.content
        except Exception as e:
            logger.error(f"Document summary generation failed: {e}")
            combined = " ".join(c.content[:200] for c in chunks[:3])
            return combined[:500]

    async def process_document(
        self,
        content: bytes,
        file_type: str,
        tenant_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        generate_summaries: bool = True,
    ) -> ProcessedDocument:
        """
        Full document processing pipeline.

        Args:
            content: Raw document bytes
            file_type: File extension
            tenant_id: Tenant ID (needed for AI summaries)
            agent_id: Agent ID (needed for AI summaries)
            generate_summaries: Whether to generate AI summaries

        Returns:
            ProcessedDocument with chunks and summary
        """
        # Extract text
        text = self.extract_text(content, file_type)

        if not text:
            return ProcessedDocument(chunks=[], total_tokens=0)

        # Chunk text
        chunks = self.chunk_text(text)

        # Calculate total tokens
        total_tokens = sum(c.token_count for c in chunks)

        # Generate document summary if AI available
        doc_summary = None
        if generate_summaries and tenant_id and agent_id and self.ai_engine:
            doc_summary = await self.generate_document_summary(
                chunks, tenant_id, agent_id
            )

        return ProcessedDocument(
            chunks=chunks,
            total_tokens=total_tokens,
            summary=doc_summary,
        )
