import dataclasses
from typing import TYPE_CHECKING, Any, Self, TypeAlias, final

from django.urls.resolvers import RoutePattern
from django.utils.functional import Promise
from typing_extensions import override

from dmr.internal.types import StrOrPromise

if TYPE_CHECKING:
    from dmr.routing import Router


@final
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class RouterMetadata:
    """
    Used to represent the metadata that we apply from router to all operations.

    Must contain all the metadata fields from :class:`dmr.routing.Router`.

    .. versionadded:: 0.15.0
    """

    tags: list[str]
    deprecated: bool
    ignore_from_spec: bool

    @classmethod
    def from_router(cls, router: 'Router') -> Self:
        """Create metadata from router instance."""
        return cls(
            tags=router.tags,
            deprecated=router.deprecated,
            ignore_from_spec=router.ignore_from_spec,
        )

    @classmethod
    def from_included(cls, router: 'Router', included: Self) -> Self:
        """Create metadata from included and including routers."""
        return cls(
            tags=router.tags + included.tags,
            deprecated=router.deprecated or included.deprecated,
            ignore_from_spec=(
                router.ignore_from_spec or included.ignore_from_spec
            ),
        )


_CapturedArgs: TypeAlias = tuple[Any, ...]
_CapturedKwargs: TypeAlias = dict[str, int | str]
_RouteMatch: TypeAlias = tuple[str, _CapturedArgs, _CapturedKwargs]


@final
class PrefixRoutePattern(RoutePattern):
    """Custom route pattern for better speed."""

    def __init__(
        self,
        route: StrOrPromise,
        name: str | None = None,
        is_endpoint: bool = False,  # noqa: FBT001, FBT002
    ) -> None:
        """Static patterns would work faster."""
        self._is_lazy = isinstance(route, Promise)
        if isinstance(route, Promise):
            # Lazy routes depend on the active language, so nothing
            # can be precomputed: we rely on Django's own matching.
            self._is_static = False
            self._prefix = ''
        else:
            idx = route.find('<')
            self._is_static = idx == -1
            self._prefix = route if self._is_static else route[:idx]
        self._is_endpoint = is_endpoint
        super().__init__(route, name, is_endpoint)  # type: ignore[arg-type]

    @override
    def match(
        self,
        path: str,
    ) -> _RouteMatch | None:
        if self._is_lazy:
            return super().match(path)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if self._is_static:
            if self._is_endpoint and path == self._prefix:
                return '', (), {}
            if not self._is_endpoint and path.startswith(self._prefix):
                return path[len(self._prefix) :], (), {}
        elif path.startswith(self._prefix):
            return super().match(path)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        return None
