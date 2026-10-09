"""Product and squared-modulus remainder trees.

Numbers may be Python ints or gmpy2.mpz values. The caller supplies integers > 1.
Levels are stored leaves first. An unpaired last child is carried to its parent.
"""

from typing import Any, Callable, Sequence

Check = Callable[[str], None]


def _no_check(stage: str) -> None:
    pass


def product_tree(values: Sequence[Any], check: Check = _no_check) -> list[list[Any]]:
    """Return leaves, their pairwise products, ..., the single root product."""
    if not values:
        return []
    levels = [list(values)]
    while len(levels[-1]) > 1:
        children = levels[-1]
        parents = []
        for left in range(0, len(children), 2):
            check("product_tree")
            if left + 1 < len(children):
                parents.append(children[left] * children[left + 1])
            else:
                parents.append(children[left])
        levels.append(parents)
    return levels


def squared_remainders(
    tree: Sequence[Sequence[Any]], check: Check = _no_check
) -> list[Any]:
    """Compute P mod n_i**2 at every leaf, without independent giant divisions.

    The invariant at a node with product V is remainder == P mod V**2.
    A child's squared product divides its parent's squared product, so reducing
    the parent's remainder again gives the correct child remainder.
    Only the current remainder level is retained.
    """
    if not tree:
        return []
    remainders = [tree[-1][0]]  # P mod P**2 == P for P > 1.
    for children in reversed(tree[:-1]):
        next_remainders = []
        for index, value in enumerate(children):
            check("remainder_tree")
            next_remainders.append(remainders[index // 2] % (value * value))
        remainders = next_remainders
    return remainders
