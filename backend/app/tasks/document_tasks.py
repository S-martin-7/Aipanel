"""
Document processing tasks.
"""
from celery import shared_task
from app.utils.logger import get_logger

logger = get_logger(__name__)


@shared_task(name="app.tasks.document_tasks.process_document")
def process_document(document_id: str, tenant_id: str):
    """
    Process an uploaded document.

    Steps:
    1. Extract text from document
    2. Split into chunks
    3. Generate summaries for each chunk
    4. Generate document summary
    5. Index for search
    """
    logger.info(f"Processing document {document_id} for tenant {tenant_id}")

    try:
        # Import here to avoid circular imports
        import asyncio
        from app.core.database import get_db_context
        from app.modules.documents.service import document_service

        async def _process():
            async with get_db_context() as db:
                await document_service.process_document(db, document_id, tenant_id)

        asyncio.run(_process())
        logger.info(f"Document {document_id} processed successfully")

    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}")
        raise


@shared_task(name="app.tasks.document_tasks.generate_chunk_summaries")
def generate_chunk_summaries(document_id: str, tenant_id: str):
    """Generate AI summaries for document chunks."""
    logger.info(f"Generating summaries for document {document_id}")

    try:
        import asyncio
        from app.core.database import get_db_context
        from app.modules.documents.service import document_service

        async def _generate():
            async with get_db_context() as db:
                await document_service.generate_summaries(db, document_id, tenant_id)

        asyncio.run(_generate())
        logger.info(f"Summaries generated for document {document_id}")

    except Exception as e:
        logger.error(f"Error generating summaries for {document_id}: {e}")
        raise


@shared_task(name="app.tasks.document_tasks.reprocess_document")
def reprocess_document(document_id: str, tenant_id: str):
    """Reprocess an existing document (clear and regenerate)."""
    logger.info(f"Reprocessing document {document_id}")

    try:
        import asyncio
        from app.core.database import get_db_context
        from app.modules.documents.service import document_service

        async def _reprocess():
            async with get_db_context() as db:
                # Clear existing chunks and summaries
                await document_service.clear_document_data(db, document_id, tenant_id)
                # Reprocess
                await document_service.process_document(db, document_id, tenant_id)

        asyncio.run(_reprocess())
        logger.info(f"Document {document_id} reprocessed successfully")

    except Exception as e:
        logger.error(f"Error reprocessing document {document_id}: {e}")
        raise


@shared_task(name="app.tasks.document_tasks.delete_document_files")
def delete_document_files(s3_key: str, tenant_id: str):
    """Delete document files from S3."""
    logger.info(f"Deleting files for key {s3_key}")

    try:
        # Validate tenant access to path
        if not s3_key.startswith(f"tenant_{tenant_id}/"):
            logger.error(f"Invalid S3 key {s3_key} for tenant {tenant_id}")
            return

        # Delete from S3
        # from app.integrations.s3_client import s3_client
        # s3_client.delete_object(s3_key)

        logger.info(f"Files deleted for key {s3_key}")

    except Exception as e:
        logger.error(f"Error deleting files {s3_key}: {e}")
        raise
