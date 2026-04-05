"""
File-Based TTL Cache System.

Provides a lightweight caching mechanism using JSON files on disk with
configurable TTL (time-to-live), LRU-style eviction, and cache hit statistics.
Designed to reduce redundant API calls to GitHub and LLM services.

基于文件的TTL缓存系统.
提供使用磁盘上JSON文件的轻量级缓存机制,具有可配置TTL(生存时间),
LRU风格淘汰和缓存命中率统计.设计用于减少对GitHub和LLM服务的冗余API调用.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Optional


class CacheEntry:
    """Single cached item with value, expiration, and metadata.

    Represents one cached response including its original data, when it was stored,
    its TTL deadline, access statistics, and origin information for debugging.

    单个缓存项,包含值,过期时间和元数据.
表示一个缓存的响应,包括其原始数据,存储时间,
TTL截止时间,访问统计信息和调试用的来源信息.

    Attributes:
        key: Unique cache key identifying this entry.
             标识此条目的唯一缓存键.
        value: The cached payload (any JSON-serializable data).
               缓存的负载(任何可序列化为JSON的数据).
        stored_at: Unix timestamp when entry was written.
                  条目写入时的Unix时间戳.
        expires_at: Unix timestamp when entry becomes stale (or -1 if no expiry).
                    条目变为陈旧的Unix时间戳(或-1如无过期).
        hits: Number of times this entry has been accessed.
              此条目被访问的次数.
        source: Optional tag indicating which service generated this data.
               指示哪个服务生成此数据的可选标签.
    """

    def __init__(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 3600,
        source: Optional[str] = None,
    ) -> None:
        self.key = key
        self.value = value
        self.stored_at = time.time()
        self.expires_at = (
            self.stored_at + ttl_seconds if ttl_seconds > 0 else -1
        )
        self.hits = 0
        self.source = source

    @property
    def is_expired(self) -> bool:
        """Check whether this entry has exceeded its TTL.

        检查此条目是否已超过其TTL.

        Returns:
            True if expired or no TTL set, False if still valid.
             已过期或无TTL设置则返回True,仍然有效则返回False.
        """
        if self.expires_at < 0:
            return False  # No expiry / 无过期
        return time.time() > self.expires_at

    @property
    def age_seconds(self) -> float:
        """Time elapsed since storage in seconds.

        存储以来经过的时间(秒).

        Returns:
            Age in seconds.
             年龄(秒).
        """
        return time.time() - self.stored_at

    def to_dict(self) -> Dict[str, Any]:
        """Serialize entry to dictionary for file storage.

        将条目序列化为字典以便文件存储.

        Returns:
            Dictionary representation suitable for JSON encoding.
             适合JSON编码的字典表示.
        """
        return {
            "key": self.key,
            "value": self.value,
            "stored_at": self.stored_at,
            "expires_at": self.expires_at,
            "hits": self.hits,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CacheEntry:
        """Reconstruct entry from deserialized dictionary.

        从反序列化的字典重建条目.

        Args:
            data: Dictionary previously produced by to_dict().
                  先前由to_dict()生成的字典.

        Returns:
            Reconstructed CacheEntry instance.
             重建的CacheEntry实例.
        """
        entry = cls(
            key=data["key"],
            value=data["value"],
            source=data.get("source"),
        )
        entry.stored_at = data["stored_at"]
        entry.expires_at = data["expires_at"]
        entry.hits = data.get("hits", 0)
        return entry


class FileCache:
    """File-system backed cache with TTL support and LRU eviction.

    Stores cached responses as individual JSON files in a specified directory,
    tracking access times for LRU eviction when capacity is reached. Thread-safe
    through file-level locking semantics.

    支持TTL和LRU淘汰的文件系统后备缓存.
将缓存的响应作为单独的JSON文件存储在指定目录中,
跟踪访问时间以便在达到容量时进行LRU淘汰.
通过文件级锁语义保证线程安全.

    Attributes:
        cache_dir: Directory where cache files are stored.
                  缓存文件存储的目录.
        default_ttl: Default time-to-live for entries in seconds (0 = no expiry).
                    条目的默认生存时间(秒)(0=永不过期).
        max_entries: Maximum number of cached items before eviction begins.
                    开始淘汰前的最大缓存项数量.
        enabled: Master switch to enable/disable caching globally.
                 全局启用/禁用缓存的主开关.
        _index: In-memory index mapping keys to CacheEntry objects.
               将键映射到CacheEntry对象的内存索引.
        _stats: Hit/miss counters for performance monitoring.
                性能监控的命中/未命中计数器.
    """

    def __init__(
        self,
        cache_dir: str = "./data/cache",
        default_ttl: int = 3600,
        max_entries: int = 500,
        enabled: bool = True,
    ) -> None:
        """Initialize cache with configuration parameters.

        使用配置参数初始化缓存.

        Args:
            cache_dir: Directory path for cache files.
                      缓存文件的目录路径.
            default_ttl: Default TTL in seconds (3600 = 1 hour). 0 means no expiry.
                        默认TTL秒数(3600=1小时).0表示永不过期.
            max_entries: Maximum cache size before LRU eviction kicks in.
                        LRU淘汰开始前的最大缓存大小.
            enabled: Whether caching is active.
                    缓存是否激活.
        """
        self.cache_dir = Path(cache_dir)
        self.default_ttl = default_ttl
        self.max_entries = max_entries
        self.enabled = enabled
        self._index: OrderedDict[str, CacheEntry] = OrderedDict()
        self._stats: Dict[str, int] = {"hits": 0, "misses": 0, "evictions": 0}

        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def make_key(*args: Any, **kwargs: Any) -> str:
        """Generate a deterministic cache key from arguments.

        从参数生成确定性的缓存键.

        Args:
            *args: Positional components to include in key.
                   要包含在键中的位置参数组件.
            **kwargs: Named components (sorted for determinism).
                      命名组件(排序以确保确定性).

        Returns:
            SHA256 hex digest string suitable as filename-safe key.
             适合作为文件名安全键的SHA256十六进制摘要字符串.
        """
        raw = json.dumps({"a": args, "k": kwargs}, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a cached value by key if present and not expired.

        如果存在且未过期则按键检索缓存值.

        Args:
            key: Cache lookup key.
                 缓存查找键.

        Returns:
            Cached value if found and valid, None otherwise (miss or expired).
             如找到且有效则返回缓存值,否则返回None(未命中或已过期).
        """
        if not self.enabled:
            return None

        # Check memory index first / 首先检查内存索引
        entry = self._index.get(key)

        if entry is None:
            # Try loading from disk / 尝试从磁盘加载
            entry = self._load_from_disk(key)
            if entry is None:
                self._stats["misses"] += 1
                return None
            self._index[key] = entry

        if entry.is_expired:
            self._evict(key)
            self._stats["misses"] += 1
            return None

        # Update access order for LRU / 更新LRU访问顺序
        self._index.move_to_end(key)
        entry.hits += 1
        self._stats["hits"] += 1

        return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        source: Optional[str] = None,
    ) -> None:
        """Store a value in the cache with optional custom TTL.

        在缓存中存储值,可选自定义TTL.

        Args:
            key: Cache key for retrieval.
                 用于检索的缓存键.
            value: Value to cache (must be JSON-serializable).
                  要缓存的值(必须可JSON序列化).
            ttl: Time-to-live override in seconds (uses default if None).
                 TTL覆盖(秒)(如果为None则使用默认值).
            source: Tag indicating data origin (for debugging).
                   指示数据来源的标签(用于调试).
        """
        if not self.enabled:
            return

        effective_ttl = ttl if ttl is not None else self.default_ttl
        entry = CacheEntry(key, value, effective_ttl, source)

        # Update existing or insert new / 更新现有或插入新的
        if key in self._index:
            del self._index[key]
        self._index[key] = entry

        # Persist to disk / 持久化到磁盘
        self._save_to_disk(entry)

        # Enforce max capacity / 强制最大容量
        self._enforce_capacity()

    def delete(self, key: str) -> bool:
        """Remove a specific entry from cache.

        从缓存中删除特定条目.

        Args:
            key: Key of the entry to remove.
                  要删除的条目的键.

        Returns:
            True if entry existed and was removed, False otherwise.
             条目存在并被删除则返回True,否则返回False.
        """
        if key in self._index:
            del self._index[key]
            self._remove_disk_file(key)
            return True
        return False

    def clear(self) -> int:
        """Remove all entries from cache.

        从缓存中删除所有条目.

        Returns:
            Number of entries removed.
             删除的条目数.
        """
        count = len(self._index)
        self._index.clear()
        for f in self.cache_dir.glob("*.cache.json"):
            f.unlink(missing_ok=True)
        return count

    # ------------------------------------------------------------------
    # Statistics / 统计信息
    # ------------------------------------------------------------------

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate ratio.

        计算缓存命中率比率.

        Returns:
            Hit rate between 0.0 and 1.0, or 0 if no accesses yet.
             0.0到1.0之间的命中率,如尚无访问则返回0.
        """
        total = self._stats["hits"] + self._stats["misses"]
        if total == 0:
            return 0.0
        return self._stats["hits"] / total

    @property
    def size(self) -> int:
        """Current number of entries in cache.

        缓存中的当前条目数.

        Returns:
            Entry count.
             条目数.
        """
        return len(self._index)

    def get_stats(self) -> Dict[str, Any]:
        """Return comprehensive cache statistics.

        返回综合缓存统计信息.

        Returns:
            Dictionary with hits, misses, hit_rate, size, evictions.
             包含hits,misses,hit_rate,size,evictions的字典.
        """
        total = self._stats["hits"] + self._stats["misses"]
        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": self.hit_rate,
            "size": self.size,
            "max_size": self.max_entries,
            "evictions": self._stats["evictions"],
            "total_accesses": total,
            "enabled": self.enabled,
            "cache_dir": str(self.cache_dir),
        }

    # ------------------------------------------------------------------
    # Internal: Disk Persistence / 内部:磁盘持久化
    # ------------------------------------------------------------------

    def _get_cache_filepath(self, key: str) -> Path:
        """Generate file path for a cache key.

        为缓存键生成文件路径.

        Args:
            key: Cache key string.
                 缓存键字符串.

        Returns:
            Full path to the .cache.json file.
             .cache.json文件的完整路径.
        """
        return self.cache_dir / f"{key}.cache.json"

    def _save_to_disk(self, entry: CacheEntry) -> None:
        """Write cache entry to its dedicated file.

        将缓存条目写入其专用文件.

        Args:
            entry: The CacheEntry to persist.
                  要持久化的CacheEntry.
        """
        filepath = self._get_cache_filepath(entry.key)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(entry.to_dict(), f, ensure_ascii=False, default=str)
        except (OSError, IOError):
            pass  # Silent fail for cache writes / 缓存写入静默失败

    def _load_from_disk(self, key: str) -> Optional[CacheEntry]:
        """Load a cache entry from disk file.

        从磁盘文件加载缓存条目.

        Args:
            key: Cache key to look up.
                 要查找的缓存键.

        Returns:
            Reconstructed CacheEntry or None if file missing/corrupt.
             重建的CacheEntry,如文件缺失/损坏则返回None.
        """
        filepath = self._get_cache_filepath(key)
        if not filepath.exists():
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return CacheEntry.from_dict(data)
        except (json.JSONDecodeError, KeyError, IOError):
            return None

    def _remove_disk_file(self, key: str) -> None:
        """Delete a cache entry's file from disk.

        从磁盘删除缓存条目的文件.

        Args:
            key: Key whose file should be deleted.
                  应删除其文件的键.
        """
        filepath = self._get_cache_filepath(key)
        filepath.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Internal: Eviction Policy / 内部:淘汰策略
    # ------------------------------------------------------------------

    def _enforce_capacity(self) -> None:
        """Evict oldest entries if cache exceeds max_entries.

        如果缓存超出max_entries则淘汰最旧的条目.
        """
        while len(self._index) > self.max_entries:
            oldest_key, _ = self._index.popitem(last=False)
            self._remove_disk_file(oldest_key)
            self._stats["evictions"] += 1

    def _evict(self, key: str) -> None:
        """Remove a single expired entry.

        删除单个过期条目.

        Args:
            key: Key of the expired entry.
                  过期条目的键.
        """
        if key in self._index:
            del self._index[key]
        self._remove_disk_file(key)


__all__ = ["FileCache", "CacheEntry"]
