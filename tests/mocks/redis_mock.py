"""
Mock implementation for Redis client.
"""
import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Union, Set
from unittest.mock import Mock
from collections import defaultdict


class RedisMock:
    """Comprehensive mock for Redis client with realistic behavior."""

    def __init__(self):
        self.data = {}  # Main key-value storage
        self.hashes = defaultdict(dict)  # Hash storage
        self.lists = defaultdict(list)  # List storage
        self.sets = defaultdict(set)  # Set storage
        self.sorted_sets = defaultdict(dict)  # Sorted set storage

        # Operation tracking
        self.operation_count = 0
        self.errors = []
        self.delay = 0.0  # Simulate network delay

        # Expiration tracking
        self.expirations = {}  # key -> timestamp

    async def get(self, key: str) -> Optional[str]:
        """Get value for key."""
        await self._simulate_delay()

        if not self._key_exists(key):
            return None

        if self._is_expired(key):
            del self.data[key]
            return None

        return self.data[key]

    async def set(self, key: str, value: Any, ex: Optional[int] = None,
                  px: Optional[int] = None, nx: bool = False, xx: bool = False) -> bool:
        """Set value for key with optional expiration and conditions."""
        await self._simulate_delay()

        # Check conditions
        exists = key in self.data
        if nx and exists:
            return False
        if xx and not exists:
            return False

        self.data[key] = str(value) if not isinstance(value, str) else value
        self._set_expiration(key, ex, px)
        return True

    async def delete(self, *keys: str) -> int:
        """Delete keys and return count of deleted keys."""
        await self._simulate_delay()

        deleted_count = 0
        for key in keys:
            if key in self.data:
                del self.data[key]
                deleted_count += 1
                if key in self.expirations:
                    del self.expirations[key]

        return deleted_count

    async def exists(self, *keys: str) -> int:
        """Check if keys exist."""
        await self._simulate_delay()

        existing_count = 0
        for key in keys:
            if self._key_exists(key) and not self._is_expired(key):
                existing_count += 1

        return existing_count

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for key in seconds."""
        await self._simulate_delay()

        if key not in self.data:
            return False

        self._set_expiration(key, seconds)
        return True

    async def ttl(self, key: str) -> int:
        """Get time to live for key."""
        await self._simulate_delay()

        if key not in self.data:
            return -2

        if key not in self.expirations:
            return -1

        remaining = self.expirations[key] - time.time()
        return max(-1, int(remaining))

    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        await self._simulate_delay()

        if pattern == "*":
            keys = [k for k in self.data.keys() if not self._is_expired(k)]
        else:
            # Simple pattern matching (supports * wildcards)
            keys = []
            for key in self.data.keys():
                if self._matches_pattern(key, pattern) and not self._is_expired(key):
                    keys.append(key)

        return keys

    async def flushall(self) -> bool:
        """Clear all data."""
        await self._simulate_delay()

        self.data.clear()
        self.hashes.clear()
        self.lists.clear()
        self.sets.clear()
        self.sorted_sets.clear()
        self.expirations.clear()

        return True

    # Hash operations
    async def hget(self, key: str, field: str) -> Optional[str]:
        """Get field value from hash."""
        await self._simulate_delay()

        if not self._key_exists(key):
            return None

        return self.hashes[key].get(field)

    async def hset(self, key: str, field: str, value: Any) -> int:
        """Set field in hash."""
        await self._simulate_delay()

        if key not in self.hashes:
            self.hashes[key] = {}

        old_value = field in self.hashes[key]
        self.hashes[key][field] = str(value) if not isinstance(value, str) else value

        return 0 if old_value else 1

    async def hgetall(self, key: str) -> Dict[str, str]:
        """Get all fields and values from hash."""
        await self._simulate_delay()

        if not self._key_exists(key):
            return {}

        return self.hashes[key].copy()

    async def hdel(self, key: str, *fields: str) -> int:
        """Delete fields from hash."""
        await self._simulate_delay()

        if key not in self.hashes:
            return 0

        deleted_count = 0
        for field in fields:
            if field in self.hashes[key]:
                del self.hashes[key][field]
                deleted_count += 1

        return deleted_count

    async def hexists(self, key: str, field: str) -> bool:
        """Check if field exists in hash."""
        await self._simulate_delay()

        return key in self.hashes and field in self.hashes[key]

    async def hlen(self, key: str) -> int:
        """Get number of fields in hash."""
        await self._simulate_delay()

        if key not in self.hashes:
            return 0

        return len(self.hashes[key])

    # List operations
    async def lpush(self, key: str, *values: Any) -> int:
        """Push values to left of list."""
        await self._simulate_delay()

        if key not in self.lists:
            self.lists[key] = []

        for value in values:
            self.lists[key].insert(0, str(value) if not isinstance(value, str) else value)

        return len(self.lists[key])

    async def rpush(self, key: str, *values: Any) -> int:
        """Push values to right of list."""
        await self._simulate_delay()

        if key not in self.lists:
            self.lists[key] = []

        for value in values:
            self.lists[key].append(str(value) if not isinstance(value, str) else value)

        return len(self.lists[key])

    async def lpop(self, key: str) -> Optional[str]:
        """Pop value from left of list."""
        await self._simulate_delay()

        if key not in self.lists or not self.lists[key]:
            return None

        return self.lists[key].pop(0)

    async def rpop(self, key: str) -> Optional[str]:
        """Pop value from right of list."""
        await self._simulate_delay()

        if key not in self.lists or not self.lists[key]:
            return None

        return self.lists[key].pop()

    async def llen(self, key: str) -> int:
        """Get length of list."""
        await self._simulate_delay()

        if key not in self.lists:
            return 0

        return len(self.lists[key])

    async def lrange(self, key: str, start: int, stop: int) -> List[str]:
        """Get range of values from list."""
        await self._simulate_delay()

        if key not in self.lists:
            return []

        return self.lists[key][start:stop+1]

    # Set operations
    async def sadd(self, key: str, *members: Any) -> int:
        """Add members to set."""
        await self._simulate_delay()

        if key not in self.sets:
            self.sets[key] = set()

        added_count = 0
        for member in members:
            member_str = str(member) if not isinstance(member, str) else member
            if member_str not in self.sets[key]:
                self.sets[key].add(member_str)
                added_count += 1

        return added_count

    async def srem(self, key: str, *members: Any) -> int:
        """Remove members from set."""
        await self._simulate_delay()

        if key not in self.sets:
            return 0

        removed_count = 0
        for member in members:
            member_str = str(member) if not isinstance(member, str) else member
            if member_str in self.sets[key]:
                self.sets[key].remove(member_str)
                removed_count += 1

        return removed_count

    async def smembers(self, key: str) -> Set[str]:
        """Get all members of set."""
        await self._simulate_delay()

        if key not in self.sets:
            return set()

        return self.sets[key].copy()

    async def scard(self, key: str) -> int:
        """Get cardinality of set."""
        await self._simulate_delay()

        if key not in self.sets:
            return 0

        return len(self.sets[key])

    async def sismember(self, key: str, member: Any) -> bool:
        """Check if member is in set."""
        await self._simulate_delay()

        member_str = str(member) if not isinstance(member, str) else member
        return key in self.sets and member_str in self.sets[key]

    # Sorted set operations
    async def zadd(self, key: str, score: float, member: Any) -> int:
        """Add member to sorted set with score."""
        await self._simulate_delay()

        if key not in self.sorted_sets:
            self.sorted_sets[key] = {}

        member_str = str(member) if not isinstance(member, str) else member
        self.sorted_sets[key][member_str] = score

        return 1

    async def zrem(self, key: str, *members: Any) -> int:
        """Remove members from sorted set."""
        await self._simulate_delay()

        if key not in self.sorted_sets:
            return 0

        removed_count = 0
        for member in members:
            member_str = str(member) if not isinstance(member, str) else member
            if member_str in self.sorted_sets[key]:
                del self.sorted_sets[key][member_str]
                removed_count += 1

        return removed_count

    async def zcard(self, key: str) -> int:
        """Get cardinality of sorted set."""
        await self._simulate_delay()

        if key not in self.sorted_sets:
            return 0

        return len(self.sorted_sets[key])

    # Utility methods
    def _key_exists(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        return key in self.data

    def _is_expired(self, key: str) -> bool:
        """Check if key is expired."""
        if key not in self.expirations:
            return False

        return time.time() > self.expirations[key]

    def _set_expiration(self, key: str, seconds: Optional[int] = None,
                       milliseconds: Optional[int] = None):
        """Set expiration for key."""
        if seconds:
            self.expirations[key] = time.time() + seconds
        elif milliseconds:
            self.expirations[key] = time.time() + (milliseconds / 1000)
        elif key in self.expirations:
            del self.expirations[key]

    def _matches_pattern(self, key: str, pattern: str) -> bool:
        """Simple pattern matching for keys."""
        # Basic implementation - in real Redis this would be more sophisticated
        if pattern == "*":
            return True

        # Simple wildcard matching
        pattern_parts = pattern.split("*")
        if len(pattern_parts) == 2:
            return key.startswith(pattern_parts[0]) and key.endswith(pattern_parts[1])

        return key == pattern

    async def _simulate_delay(self):
        """Simulate network delay."""
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        self.operation_count += 1

    # Configuration methods
    def set_delay(self, seconds: float):
        """Set delay for all operations."""
        self.delay = seconds

    def add_error(self, error: str):
        """Add an error to be raised on next operation."""
        self.errors.append(error)

    def clear_errors(self):
        """Clear all errors."""
        self.errors.clear()

    def get_operation_count(self) -> int:
        """Get total operation count."""
        return self.operation_count

    def get_stats(self) -> Dict[str, Any]:
        """Get mock Redis statistics."""
        return {
            "keys": len(self.data),
            "hashes": len(self.hashes),
            "lists": len(self.lists),
            "sets": len(self.sets),
            "sorted_sets": len(self.sorted_sets),
            "operations": self.operation_count,
            "errors": len(self.errors)
        }


class RedisMockBuilder:
    """Builder for creating customized Redis mocks."""

    def __init__(self):
        self.config = {
            "delay": 0.0,
            "prepopulate_data": {},
            "errors": []
        }

    def with_delay(self, seconds: float) -> 'RedisMockBuilder':
        """Configure operation delay."""
        self.config["delay"] = seconds
        return self

    def with_data(self, key: str, value: Any) -> 'RedisMockBuilder':
        """Pre-populate with key-value data."""
        self.config["prepopulate_data"][key] = value
        return self

    def with_error(self, error: str) -> 'RedisMockBuilder':
        """Add error to be raised."""
        self.config["errors"].append(error)
        return self

    def build(self) -> RedisMock:
        """Build the configured Redis mock."""
        mock = RedisMock()

        # Set delay
        if self.config["delay"] > 0:
            mock.set_delay(self.config["delay"])

        # Pre-populate data
        for key, value in self.config["prepopulate_data"].items():
            mock.data[key] = str(value) if not isinstance(value, str) else value

        # Add errors
        for error in self.config["errors"]:
            mock.add_error(error)

        return mock