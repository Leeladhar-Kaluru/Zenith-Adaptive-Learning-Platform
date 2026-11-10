import os
import sys
import pytest

if sys.platform == "win32":
    from asyncio.proactor_events import BaseProactorEventLoop
    class PipeWrapper:
        def __init__(self, fd): self.fd = fd
        def fileno(self): return self.fd
        def setblocking(self, b): pass
        def close(self): pass
    BaseProactorEventLoop._make_self_pipe = lambda self: (setattr(self, '_ssock', PipeWrapper(os.pipe()[0])), setattr(self, '_csock', PipeWrapper(os.pipe()[1])), setattr(self, '_internal_fds', self._internal_fds + 1))
    BaseProactorEventLoop._close_self_pipe = lambda self: None
    BaseProactorEventLoop._loop_self_reading = lambda self, f=None: None

# Ensure project root and backend are on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from e2e_tests.helpers.api_client import E2EApiClient
from e2e_tests.helpers.auth import (
    create_test_student_headers,
    create_test_teacher_headers,
    create_anonymous_headers,
)
from e2e_tests.helpers.bkt_oracle import BKTOracle
from e2e_tests.helpers.math_verifier import MathVerifierOracle

@pytest.fixture
def client():
    """Default client with anonymous headers."""
    return E2EApiClient(headers=create_anonymous_headers())

@pytest.fixture
def student_client():
    """Client authenticated as a student."""
    return E2EApiClient(headers=create_test_student_headers())

@pytest.fixture
def teacher_client():
    """Client authenticated as a teacher."""
    return E2EApiClient(headers=create_test_teacher_headers())

@pytest.fixture
def bkt_oracle():
    """Authoritative BKT mathematical reference oracle."""
    return BKTOracle()

@pytest.fixture
def math_verifier():
    """Mathematical solver and equation verifier oracle."""
    return MathVerifierOracle()
