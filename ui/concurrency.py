from __future__ import annotations

import inspect
import threading
from typing import Any, Callable


_completed_lock = threading.Lock()
completed = []


def has_positional_arg(signature: inspect.Signature) -> bool:
    viable_params = filter(lambda x: x.kind not in [inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.VAR_KEYWORD], signature.parameters)
    try:
        next(viable_params)
        return True
    except StopIteration:
        return False


class DeferredTask:
    def __init__(self, executor: Callable):
        self.__resolved = False

        self.__executor = executor
        self.__lock = threading.Lock()
        self.__after = []
    
    def run(self, *args):
        t = threading.Thread(target=self._run, args=args, daemon=True)
        t.start()
    
    def _run(self, *args):
        self.__result = self.__executor(*args)
        self.__resolved = True

        global completed
        global _completed_lock
        with _completed_lock:
            completed.append(self)
    
    def _complete(self):
        for next_task in self.__after:
            signature = inspect.signature(next_task.__executor)
            if has_positional_arg(signature):
                next_task.run(self.__result)
            else:
                next_task.run()
    
    def then(self, callback) -> DeferredTask:
        deferred = DeferredTask(callback)

        if self.__resolved:
            deferred.run(self.__result)
        else:
            self.__after.append(deferred)

        return deferred
    
    @property
    def result(self):
        if self.__resolved:
            return self.__result
        else:
            return None
    
    @property
    def lock(self) -> threading.Lock:
        return self.__lock
    

main_queue = []
_main_queue_lock = threading.Lock()


def process():
    global completed
    global _completed_lock

    with _completed_lock:
        for deferred in completed:
            deferred._complete()

        completed = []
    
    global main_queue
    with _main_queue_lock:
        for callback, args, kwargs in main_queue:
            callback(*args, **kwargs)
        
        main_queue = []


def _exec(event: threading.Event, executor, *args, **kwargs):
    executor(*args, **kwargs)
    event.set()

def main(executor, *args, **kwargs):
    if threading.current_thread() is threading.main_thread():
        executor(*args, **kwargs)
    else:
        event = threading.Event()

        global main_queue
        global _main_queue_lock
        with _main_queue_lock:
            main_queue.append((_exec, (event, executor) + args, kwargs))
    
        event.wait()
