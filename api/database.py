"""
Async database connection and session management.
"""
import ssl
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from api.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()

# Build connect_args for SSL if required by cloud PostgreSQL (e.g. Neon.tech)
_connect_args = {}
if "ssl=require" in settings.database_url or "sslmode=require" in settings.database_url:
    _ssl_ctx = ssl.create_default_context()
    _ssl_ctx.check_hostname = False
    _ssl_ctx.verify_mode = ssl.CERT_NONE
    _connect_args["ssl"] = _ssl_ctx

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=5,       # Reduced for free-tier connection limits
    max_overflow=3,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async DB session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Dispose engine on shutdown."""
    await engine.dispose()
