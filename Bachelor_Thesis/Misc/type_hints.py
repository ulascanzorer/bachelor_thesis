from typing import Optional, Any, Sequence, Callable

def add(x: int, y: int) -> int:
    return x + y

def foo(func: Callable[[int, int], int]) -> None:
    func(1, 2)

foo(add)

s: str = None