import pytest
from smartypants import config
from smartypants import worker
from queue import Queue


def test_worker_init():
    c = config.Config()
    w = worker.Worker(c, Queue())
    assert isinstance(w, worker.Worker)
