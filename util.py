import typing


def get_yes_no(question: str, default: bool = True):
    result = None
    while result not in ["y", "n", ""]:
        if result is not None:
            print("Invalid response '%s'. Please input a 'y' or 'n'. %s" % (result, question))

        result = input(question).strip().lower()
    
    if result == "y":
        return True
    elif result == "n":
        return False
    else:
        return default
    

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
