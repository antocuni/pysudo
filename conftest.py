import pytest
def pytest_addoption(parser):
    parser.addoption("--interactive", action="store_true",
        help="run REAL interactive tests to get sudo")
