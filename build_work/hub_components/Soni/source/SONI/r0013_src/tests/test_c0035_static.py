"""Superseded by R0009 direct-render regression tests.

The previous assertions required the RC2 signal/snapshot gate that caused the
visible runtime regression. Functional coverage is retained in
test_r0009_regression_restore.py and the service/parser tests.
"""

import pytest

pytestmark = pytest.mark.skip(reason="superseded by R0009 regression restoration")
