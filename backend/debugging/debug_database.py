"""
Script de debugging para verificar conexion a base de datos.

Uso:
    python backend/debugging/debug_database.py
"""

import asyncio
import sys
from pathlib import Path

# Agregar backend al path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.config import settings
from app.core.database import init_database, close_database
from app.utils.logger import setup_logging, get_logger

logger = get_logger(__name__)


async def test_database_connection():
    """Test de conexion a base de datos."""

    print("=" * 60)
    print("DATABASE CONNECTION TEST")
    print("=" * 60)

    print(f"\nDatabase URL: {settings.DATABASE_URL}")
    print(f"Environment: {settings.ENVIRONMENT}")

    print("\nAttempting to connect...")

    try:
        # Inicializar base de datos
        await init_database()
        print("SUCCESS: Database connection established")

        # Aqui puedes agregar queries de prueba
        # Por ejemplo:
        # result = await db.execute("SELECT 1")
        # print(f"Test query result: {result}")

        print("\nTest completed successfully!")

    except Exception as e:
        print(f"ERROR: Database connection failed")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        import traceback
        print("\nStack trace:")
        print(traceback.format_exc())

    finally:
        print("\nClosing connection...")
        await close_database()
        print("Connection closed")

    print("=" * 60)


async def test_database_tables():
    """Test de existencia de tablas."""

    print("\n" + "=" * 60)
    print("DATABASE TABLES TEST")
    print("=" * 60)

    try:
        await init_database()

        # TODO: Verificar que tablas existen
        # tables = await db.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        # print(f"\nFound {len(tables)} tables:")
        # for table in tables:
        #     print(f"  - {table}")

        print("\nTable verification not implemented yet")

    except Exception as e:
        print(f"ERROR: {e}")

    finally:
        await close_database()

    print("=" * 60)


async def main():
    """Main entry point."""

    setup_logging()

    print("\nStarting database debugging...")
    print("This script will test database connectivity\n")

    # Test 1: Conexion basica
    await test_database_connection()

    # Test 2: Verificar tablas
    await test_database_tables()

    print("\nDebugging completed!")


if __name__ == "__main__":
    asyncio.run(main())
