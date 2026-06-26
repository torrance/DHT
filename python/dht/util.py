from typing import Iterable, TypeVar


T = TypeVar("T")


def flatten(xss: Iterable[list[T]]) -> list[T]:
    return [x for xs in xss for x in xs]
