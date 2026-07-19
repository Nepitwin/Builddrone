"""Custom exceptions for the Builddrone package."""


class DroneException(Exception):
    """Base exception raised by Builddrone-specific runtime errors.

    Use this exception as the common parent for errors that originate from
    the Builddrone domain, so callers can catch framework-level failures in a
    single place while still allowing more specific exception types later.
    """
