# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests verifying onex.node_package entry point is absent post-migration.

After all nodes migrated to omnimarket (OMN-8302), omnimemory no longer
declares an onex.node_package entry point.  The runtime must not attempt
to discover handlers from this package.
"""

import importlib.metadata

import pytest


@pytest.mark.unit
def test_node_package_entry_point_absent() -> None:
    """onex.node_package entry point must NOT be declared after migration."""
    eps = importlib.metadata.entry_points(group="onex.node_package")
    names = [ep.name for ep in eps]
    assert "omnimemory" not in names, (
        "omnimemory must not declare onex.node_package after node migration "
        f"(OMN-8302). Found: {names}"
    )
