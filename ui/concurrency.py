from __future__ import annotations

import functools
import inspect
import threading
import time
import tkinter
from typing import Any, Callable


_completed_lock = threading.Lock()
completed = []


def has_positional_arg(signature: inspect.Signature) -> bool:
    viable_params = filter(lambda x: x.kind not in [inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.VAR_KEYWORD], signature.parameters.values())
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
    
    def wait(self) -> Any:
        while not self.__resolved:
            time.sleep(0.001)
        
        return self.result
    

main_queue = []
task_results = {}
_main_queue_lock = threading.Lock()
_task_results_lock = threading.Lock()

task_id = 0


def next_task_id():
    global task_id
    use_id = task_id
    task_id += 1
    return use_id


def process():
    global completed
    global _completed_lock

    with _completed_lock:
        for deferred in completed:
            deferred._complete()

        completed = []
    
    global main_queue

    with _main_queue_lock:
        to_process = main_queue
        main_queue = []
    
    for callback, args, kwargs in to_process:
        callback(*args, **kwargs)


def _exec(task_id: int, event: threading.Event, executor, *args, **kwargs):
    result = executor(*args, **kwargs)

    global task_results
    global _task_results_lock
    with _task_results_lock:
        task_results[task_id] = result

    event.set()

def with_event(event: threading.Event, executor, *args, **kwargs):
    @functools.wraps(executor)
    def wrapped(*args, **kwargs):
        executor(*args, **kwargs)
        event.set()

    return wrapped

def event_timer(event: threading.Event, seconds: int):
    time.sleep(seconds)
    event.set()

def main(executor, *args, **kwargs):
    if threading.current_thread() is threading.main_thread():
        executor(*args, **kwargs)
    else:
        event = threading.Event()

        global main_queue
        global _main_queue_lock
    
        task_id = next_task_id()

        if has_positional_arg(inspect.signature(executor)):
            queue_args = (task_id, event, executor) + args
        else:
            queue_args = (task_id, event, executor)

        with _main_queue_lock:
            main_queue.append((_exec, queue_args, kwargs))
    
        event.wait()
        
        global task_results
        global _task_results_lock
        with _task_results_lock:
            return task_results.pop(task_id)


def update_app(root: tkinter.Tk):
    process()
    root.update()
    root.update_idletasks()


def wait_window(window: tkinter.Toplevel, root: tkinter.Tk, is_running: tkinter.BooleanVar | None = None):
    try:
        check_running = True
        while check_running:
            window.state()
            update_app(root)
            check_running = is_running.get() if is_running else True
    except tkinter.TclError:
        pass
