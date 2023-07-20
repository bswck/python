"""Tests for the `rendering` module."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pytest
from griffe.collections import ModulesCollection
from griffe.tests import temporary_visited_module

from mkdocstrings_handlers.python import rendering

if TYPE_CHECKING:
    from markupsafe import Markup


@pytest.mark.parametrize(
    "code",
    [
        "print('Hello')",
        "aaaaa(bbbbb, ccccc=1) + ddddd.eeeee[ffff] or {ggggg: hhhhh, iiiii: jjjjj}",
    ],
)
def test_format_code(code: str) -> None:
    """Assert code can be Black-formatted.

    Parameters:
        code: Code to format.
    """
    for length in (5, 100):
        assert rendering.do_format_code(code, length)


@pytest.mark.parametrize(
    ("name", "signature"),
    [("Class.method", "(param: str = 'hello') -> 'OtherClass'")],
)
def test_format_signature(name: Markup, signature: str) -> None:
    """Assert signatures can be Black-formatted.

    Parameters:
        signature: Signature to format.
    """
    for length in (5, 100):
        assert rendering._format_signature(name, signature, length)


@dataclass
class _FakeObject:
    name: str
    inherited: bool = False


@pytest.mark.parametrize(
    ("names", "filter_params", "expected_names"),
    [
        (["aa", "ab", "ac", "da"], {"filters": [(re.compile("^a[^b]"), True)]}, {"ab", "da"}),
        (["aa", "ab", "ac", "da"], {"members_list": ["aa", "ab"]}, {"aa", "ab"}),
    ],
)
def test_filter_objects(names: list[str], filter_params: dict[str, Any], expected_names: set[str]) -> None:
    """Assert the objects filter works correctly.

    Parameters:
        names: Names of the objects.
        filter_params: Parameters passed to the filter function.
        expected_names: Names expected to be kept.
    """
    objects = {name: _FakeObject(name) for name in names}
    filtered = rendering.do_filter_objects(objects, **filter_params)  # type: ignore[arg-type]
    filtered_names = {obj.name for obj in filtered}
    assert set(filtered_names) == set(expected_names)


@pytest.mark.parametrize(
    ("members", "inherited_members", "expected_names"),
    [
        (True, True, {"base", "main"}),
        (True, False, {"main"}),
        (True, ["base"], {"base", "main"}),
        (True, [], {"main"}),
        (False, True, {"base"}),
        (False, False, set()),
        (False, ["base"], {"base"}),
        (False, [], set()),
        ([], True, {"base"}),
        ([], False, set()),
        ([], ["base"], {"base"}),
        ([], [], set()),
        (None, True, {"base", "main"}),
        (None, False, {"main"}),
        (None, ["base"], {"base", "main"}),
        (None, [], {"main"}),
        (["base"], True, {"base"}),
        (["base"], False, set()),
        (["base"], ["base"], {"base"}),
        (["base"], [], set()),
        (["main"], True, {"main"}),
        (["main"], False, {"main"}),
        (["main"], ["base"], {"base", "main"}),
        (["main"], [], {"main"}),
    ],
)
def test_filter_inherited_members(
    members: bool | list[str] | None,
    inherited_members: bool | list[str],
    expected_names: list[str],
) -> None:
    """Test inherited members filtering.

    Parameters:
        members: Members option (parametrized).
        inherited_members: Inherited members option (parametrized).
        expected_names: The expected result as a list of member names.
    """
    collection = ModulesCollection()
    with temporary_visited_module(
        """
        class Base:
            def base(self): ...

        class Main(Base):
            def main(self): ...
        """,
        modules_collection=collection,
    ) as module:
        collection["module"] = module
        objects = module["Main"].all_members
        filtered = rendering.do_filter_objects(objects, members_list=members, inherited_members=inherited_members)
        names = {obj.name for obj in filtered}
        assert names == expected_names


@pytest.mark.parametrize(
    ("order", "members_list", "expected_names"),
    [
        (rendering.Order.alphabetical, None, ["a", "b", "c"]),
        (rendering.Order.source, None, ["c", "b", "a"]),
        (rendering.Order.alphabetical, ["c", "b"], ["c", "b"]),
        (rendering.Order.source, ["a", "c"], ["a", "c"]),
        (rendering.Order.alphabetical, [], ["a", "b", "c"]),
        (rendering.Order.source, [], ["c", "b", "a"]),
        (rendering.Order.alphabetical, True, ["a", "b", "c"]),
        (rendering.Order.source, False, ["c", "b", "a"]),
    ],
)
def test_ordering_members(order: rendering.Order, members_list: list[str | None], expected_names: list[str]) -> None:
    """Assert the objects are correctly ordered.

    Parameters:
        order: The order to use (alphabetical or source).
        members_list: The user specified members list.
        expected_names: The expected ordered list of object names.
    """

    class Obj:
        def __init__(self, name: str, lineno: int | None = None) -> None:
            self.name = name
            self.lineno = lineno

    members = [Obj("a", 10), Obj("b", 9), Obj("c", 8)]
    ordered = rendering.do_order_members(members, order, members_list)  # type: ignore[arg-type]
    assert [obj.name for obj in ordered] == expected_names
