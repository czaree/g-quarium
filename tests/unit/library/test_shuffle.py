import random
from pathlib import Path

from gquarium.library.shuffle import ShuffleBag


def test_bag_plays_everything_once_per_cycle():
    """
    validate shuffle system plays every track exactly once
    """
    items = [Path(f"{i}.mp3") for i in range(5)]
    bag = ShuffleBag(lambda: items, random.Random(1))
    assert sorted(bag.next() for _ in range(5)) == sorted(items)


def test_bag_never_repeats_across_cycle_boundary():
    """
    validate no single track repeats in a cycle
    """
    items = [Path("a.mp3"), Path("b.mp3")]
    bag = ShuffleBag(lambda: items, random.Random(3))
    seq = [bag.next() for _ in range(200)]
    assert all(x != y for x, y in zip(seq, seq[1:], strict=False))


def test_bag_empty_library_returns_none_and_recovers():
    """
    validate an empty music library returns nothing, but updates
    when a new track is added
    """
    items: list[Path] = []
    bag = ShuffleBag(lambda: items)
    assert bag.next() is None
    items.append(Path("new.mp3"))
    assert bag.next() == Path("new.mp3")
