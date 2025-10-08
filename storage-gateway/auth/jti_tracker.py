"""
JTI Tracker - Single-Use Token Enforcement

Uses Redis to track JWT IDs (jti) and prevent token replay attacks.
"""
import logging
import redis
from typing import Optional
from datetime import datetime, timezone

logger = logging.getLogger('storage-gateway.auth.jti_tracker')


class JTITrackerError(Exception):
    """Base exception for JTI tracker errors."""
    pass


class JTIAlreadyUsedError(JTITrackerError):
    """Exception raised when token has already been used."""
    pass


class JTITracker:
    """
    Tracks used JWT IDs in Redis to enforce single-use tokens.

    Features:
    - Store jti with TTL matching token expiration
    - Check if jti already used (replay prevention)
    - Automatic cleanup via Redis TTL
    - Connection pooling for performance
    """

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None,
        key_prefix: str = "storage:jti:"
    ):
        """
        Initialize JTI tracker.

        :param redis_host: Redis server hostname
        :param redis_port: Redis server port
        :param redis_db: Redis database number
        :param redis_password: Redis password (optional)
        :param key_prefix: Prefix for Redis keys
        """
        self.key_prefix = key_prefix

        # Initialize Redis connection pool
        pool = redis.ConnectionPool(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=True,
            max_connections=20
        )

        self.redis_client = redis.Redis(connection_pool=pool)

        # Test connection
        try:
            self.redis_client.ping()
            logger.info(f"JTI Tracker connected to Redis: {redis_host}:{redis_port}/{redis_db}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise JTITrackerError(f"Redis connection failed: {e}")

    def _get_key(self, jti: str) -> str:
        """
        Generate Redis key for jti.

        :param jti: JWT ID
        :return: Redis key
        """
        return f"{self.key_prefix}{jti}"

    def check_and_mark_used(self, jti: str, ttl: int, metadata: Optional[dict] = None) -> None:
        """
        Check if jti has been used, and mark it as used if not.

        This is an atomic operation using Redis SET with NX (set if not exists).

        :param jti: JWT ID from token
        :param ttl: Time to live in seconds (should match token expiration)
        :param metadata: Optional metadata to store (e.g., user_uuid, path, timestamp)
        :raises JTIAlreadyUsedError: If jti has already been used
        :raises JTITrackerError: If Redis operation fails
        """
        key = self._get_key(jti)

        # Prepare value to store
        if metadata:
            # Store as JSON-like string
            value = str(metadata)
        else:
            value = datetime.now(timezone.utc).isoformat()

        try:
            # Atomic check-and-set: SET key value EX ttl NX
            # Returns True if key was set, False if key already exists
            was_set = self.redis_client.set(
                key,
                value,
                ex=ttl,
                nx=True  # Only set if key doesn't exist
            )

            if not was_set:
                # Key already exists = token already used
                logger.warning(
                    f"Token replay detected",
                    extra={
                        "jti": jti,
                        "existing_value": self.redis_client.get(key)
                    }
                )
                raise JTIAlreadyUsedError(f"Token has already been used (jti: {jti})")

            logger.info(
                f"JTI marked as used",
                extra={
                    "jti": jti,
                    "ttl": ttl,
                    "metadata": metadata
                }
            )

        except JTIAlreadyUsedError:
            # Re-raise our custom exception
            raise

        except redis.RedisError as e:
            logger.error(f"Redis error during jti check: {e}")
            raise JTITrackerError(f"Failed to check jti: {e}")

    def is_used(self, jti: str) -> bool:
        """
        Check if jti has been used (non-atomic, for testing/debugging).

        :param jti: JWT ID
        :return: True if jti exists in Redis, False otherwise
        """
        key = self._get_key(jti)

        try:
            return self.redis_client.exists(key) > 0
        except redis.RedisError as e:
            logger.error(f"Redis error checking jti existence: {e}")
            raise JTITrackerError(f"Failed to check jti existence: {e}")

    def get_ttl(self, jti: str) -> Optional[int]:
        """
        Get remaining TTL for jti (for debugging).

        :param jti: JWT ID
        :return: Remaining TTL in seconds, or None if key doesn't exist
        """
        key = self._get_key(jti)

        try:
            ttl = self.redis_client.ttl(key)
            if ttl == -2:
                # Key doesn't exist
                return None
            elif ttl == -1:
                # Key exists but has no expiration
                logger.warning(f"JTI key has no expiration: {jti}")
                return -1
            else:
                return ttl
        except redis.RedisError as e:
            logger.error(f"Redis error getting TTL: {e}")
            raise JTITrackerError(f"Failed to get TTL: {e}")

    def revoke_token(self, jti: str) -> bool:
        """
        Manually revoke a token by deleting its jti.

        WARNING: This allows the token to be used again!
        Only use for administrative cleanup.

        :param jti: JWT ID to revoke
        :return: True if key was deleted, False if it didn't exist
        """
        key = self._get_key(jti)

        try:
            deleted = self.redis_client.delete(key)
            if deleted:
                logger.info(f"JTI revoked: {jti}")
            return bool(deleted)
        except redis.RedisError as e:
            logger.error(f"Redis error revoking jti: {e}")
            raise JTITrackerError(f"Failed to revoke jti: {e}")

    def health_check(self) -> bool:
        """
        Check Redis connection health.

        :return: True if Redis is reachable, False otherwise
        """
        try:
            return self.redis_client.ping()
        except redis.RedisError:
            return False
