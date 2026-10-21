"""Wait on a ROS future while letting the executor run other callbacks."""
from rclpy.task import Future


async def wait_with_timeout(node, source, seconds, label):
    output = Future()

    def expired():
        if not output.done():
            output.set_exception(TimeoutError(label + ' timed out.'))

    def completed(future):
        if output.done():
            return
        if future.cancelled():
            output.set_exception(RuntimeError(label + ' canceled.'))
        elif future.exception() is not None:
            output.set_exception(future.exception())
        else:
            output.set_result(future.result())

    timer = node.create_timer(seconds, expired)
    source.add_done_callback(completed)
    try:
        return await output
    finally:
        node.destroy_timer(timer)
