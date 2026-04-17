from typing import Callable, Generic, Hashable, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class MemoCache(Generic[K, V]):
    def __init__(self):
        self._data: dict[K, V] = {}

    def get(self, key: K) -> V | None:
        return self._data.get(key)

    def set(self, key: K, value: V):
        self._data[key] = value

    def get_or_compute(self, key: K, factory: Callable[[], V]) -> V:
        cached = self._data.get(key)
        if cached is not None:
            return cached
        value = factory()
        self._data[key] = value
        return value

