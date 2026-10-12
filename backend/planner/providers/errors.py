class ProviderError(Exception):
    """An upstream API failed or rejected the request."""


class NoRouteError(ProviderError):
    """The routing API found no route between the points."""
