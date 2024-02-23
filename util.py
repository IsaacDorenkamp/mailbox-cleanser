import functools
import typing


T = typing.TypeVar("T")


def produce_batches(iterable: typing.Iterable[T], batch_size: int) -> typing.Generator[list[T], None, None]:
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than or equal to one.")

    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) == batch_size:
            yield batch
            batch = []
    
    if batch:
        yield batch


_version_registry = {}


def version(version_no):
    def decorator(fn):
        entry = _version_registry.get(fn.__qualname__)

        if entry:
            if version_no in entry.__versions__:
                raise ValueError("Version '%s' already exists for function '%s'" % (version_no, fn.__qualname__))
            else:
                entry.__versions__[version_no] = fn
                return entry
        else:
            @functools.wraps(fn)
            def version_fn(*args, version: str, **kwargs):
                dispatch = version_fn.__versions__.get(version)
                if dispatch:
                    return dispatch(*args, **kwargs)
                else:
                    raise ValueError("No version '%s' for function '%s'" % (version, fn.__qualname__))
            
            version_fn.__versions__ = {
                version_no: fn
            }
            
            _version_registry[fn.__qualname__] = version_fn
            return version_fn

    
    return decorator
