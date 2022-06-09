from concurrent.futures import Future


def _copy_future_state(source: Future, destination: Future) -> None:
    """
    Copies the state of a future into another.

    Warning: it is only safe to copy future states once the source future has
    been resolved. That is, either finished or failed.

    :param source: future state to be copied.
    :param destination: object where the source state will be copied into.
    :returns None
    """
    if source.cancelled():
        destination.cancel()
    if not destination.set_running_or_notify_cancel():
        return
    exception = source.exception()
    if exception is not None:
        destination.set_exception(exception)
    else:
        destination.set_result(source.result())


def chain_to_future(future, fn, *args, **kwargs):
    """
    Calls fn once the future is done and returns a new future.

    :param future: Future that the call to fn will be chained to.
    :param fn: callable to be called once the future is done. It receives the result of the future as the first
    parameter together with the args and kwargs. It's expected to also return a future.
    :param args: Arguments to append to the call to fn. Note that the first argument will the result of the future.
    :param kwargs: Keyword arguments to append to the call to fn. Note that the first argument will be the result of the future.
    :return:
    """
    chained_future = Future()
    chained_future.set_running_or_notify_cancel()

    def first_future_done_callback(first_future_done: Future):
        try:
            first_future_result = first_future_done.result()
            fn_future = fn(first_future_result, *args, **kwargs)
            copy = lambda: _copy_future_state(fn_future, chained_future)
            # when fn_future is done, copy it's state to chained_future closure
            fn_future.add_done_callback(copy)
        except BaseException as e:
            chained_future.set_exception(e)

    future.add_done_callback(first_future_done_callback)

    return chained_future
