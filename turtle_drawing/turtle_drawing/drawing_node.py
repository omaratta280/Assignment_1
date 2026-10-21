"""Person 2: reset service and square action using exactly four movement goals."""
import math

import rclpy
from action_msgs.msg import GoalStatus, GoalStatusArray
from rclpy.action import ActionClient, ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from std_srvs.srv import Empty, Trigger
from turtlesim.srv import SetPen, TeleportAbsolute
from turtle_interfaces.action import DrawSquare, GoToPose
from .async_tools import wait_with_timeout

START = 5.544444561004639


def square_corners(length):
    return [
        (START + length, START, math.pi / 2.0),
        (START + length, START + length, math.pi),
        (START, START + length, -math.pi / 2.0),
        (START, START, 0.0),
    ]


class DrawingNode(Node):
    def __init__(self):
        super().__init__('drawing_node')
        self.group = ReentrantCallbackGroup()
        self.square_busy = False
        self.reset_busy = False
        self.allow_square_reset = False
        self.child_goal = None
        self.movement_busy = False
        status_qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.status_sub = self.create_subscription(
            GoalStatusArray, '/go_to_pose/_action/status', self.on_movement_status, status_qos)
        self.clear_client = self.create_client(Empty, '/clear', callback_group=self.group)
        self.pen_client = self.create_client(SetPen, '/turtle1/set_pen', callback_group=self.group)
        self.teleport_client = self.create_client(
            TeleportAbsolute, '/turtle1/teleport_absolute', callback_group=self.group)
        self.reset_server = self.create_service(
            Trigger, '/reset_turtle', self.reset_callback, callback_group=self.group)
        self.reset_client = self.create_client(Trigger, '/reset_turtle', callback_group=self.group)
        self.movement_client = ActionClient(self, GoToPose, '/go_to_pose', callback_group=self.group)
        self.square_server = ActionServer(
            self, DrawSquare, '/draw_square', execute_callback=self.draw_square,
            goal_callback=self.accept_square, cancel_callback=self.cancel_square,
            callback_group=self.group)
        self.get_logger().info('Drawing node ready: /reset_turtle and /draw_square')

    def on_movement_status(self, message):
        running = (GoalStatus.STATUS_ACCEPTED, GoalStatus.STATUS_EXECUTING, GoalStatus.STATUS_CANCELING)
        self.movement_busy = any(item.status in running for item in message.status_list)

    async def call_service(self, client, request):
        if not client.service_is_ready():
            raise RuntimeError(client.srv_name + ' is not ready. Wait for all nodes to start.')
        return await wait_with_timeout(self, client.call_async(request), 8.0, client.srv_name)

    @staticmethod
    def pen_request(off):
        return SetPen.Request(r=255, g=255, b=255, width=3, off=off)

    async def reset_callback(self, request, response):
        if self.reset_busy or self.movement_busy or (self.square_busy and not self.allow_square_reset):
            response.success = False
            response.message = 'Reset refused: reset, movement or square already running.'
            return response
        self.allow_square_reset = False
        self.reset_busy = True
        try:
            await self.call_service(self.pen_client, self.pen_request(1))
            await self.call_service(self.teleport_client,
                                    TeleportAbsolute.Request(x=START, y=START, theta=0.0))
            await self.call_service(self.clear_client, Empty.Request())
            await self.call_service(self.pen_client, self.pen_request(0))
            response.success = True
            response.message = 'Screen cleared; turtle returned to its original pose.'
        except Exception as error:
            response.success, response.message = False, str(error)
            try:
                await self.call_service(self.pen_client, self.pen_request(0))
            except Exception:
                pass
        finally:
            self.reset_busy = False
        return response

    def accept_square(self, request):
        length = request.side_length
        valid = math.isfinite(length) and 0.2 <= length <= 5.0
        if self.square_busy or self.reset_busy or self.movement_busy or not valid:
            self.get_logger().warning('Square rejected: busy or side length outside [0.2, 5.0].')
            return GoalResponse.REJECT
        self.square_busy = True
        return GoalResponse.ACCEPT

    def cancel_square(self, goal_handle):
        if self.child_goal is not None:
            self.child_goal.cancel_goal_async()
        return CancelResponse.ACCEPT

    async def draw_square(self, goal_handle):
        result = DrawSquare.Result(success=False, message='Square did not complete.')
        try:
            if not self.movement_client.server_is_ready():
                raise RuntimeError('/go_to_pose is not ready. Launch all nodes first.')
            goal_handle.publish_feedback(DrawSquare.Feedback(current_side=0, phase='RESET'))
            self.allow_square_reset = True
            response = await self.call_service(self.reset_client, Trigger.Request())
            if not response.success:
                raise RuntimeError(response.message)
            for number, (x, y, yaw) in enumerate(square_corners(goal_handle.request.side_length), 1):
                if goal_handle.is_cancel_requested:
                    goal_handle.canceled()
                    result.message = 'Square canceled.'
                    return result
                goal_handle.publish_feedback(DrawSquare.Feedback(current_side=number, phase='DRAWING'))
                goal = GoToPose.Goal()
                goal.target.x, goal.target.y, goal.target.yaw = x, y, yaw
                self.get_logger().info(f'SQUARE side {number}/4: sending one goToPose goal.')
                acceptance = self.movement_client.send_goal_async(goal)
                # If acceptance arrives only after our timeout, cancel the late goal.
                abandoned = [False]
                def stop_late_goal(future, flag=abandoned):
                    if flag[0] and not future.cancelled() and future.exception() is None:
                        late = future.result()
                        if late.accepted:
                            late.cancel_goal_async()
                acceptance.add_done_callback(stop_late_goal)
                try:
                    self.child_goal = await wait_with_timeout(self, acceptance, 8.0, 'Goal acceptance')
                except Exception:
                    abandoned[0] = True
                    raise
                if not self.child_goal.accepted:
                    self.child_goal = None
                    raise RuntimeError(f'goToPose rejected side {number}.')
                if goal_handle.is_cancel_requested:
                    await wait_with_timeout(self, self.child_goal.cancel_goal_async(), 8.0, 'Child cancel')
                reply = await wait_with_timeout(self, self.child_goal.get_result_async(), 310.0, 'Movement result')
                self.child_goal = None
                if goal_handle.is_cancel_requested:
                    goal_handle.canceled()
                    result.message = 'Square canceled; movement stopped.'
                    return result
                if reply.status != GoalStatus.STATUS_SUCCEEDED or not reply.result.success:
                    raise RuntimeError(f'Side {number} failed: {reply.result.message}')
            goal_handle.publish_feedback(DrawSquare.Feedback(current_side=4, phase='DONE'))
            goal_handle.succeed()
            result.success = True
            result.message = 'Square completed using exactly four goToPose goals.'
        except Exception as error:
            if self.child_goal is not None and self.child_goal.accepted:
                try:
                    await wait_with_timeout(self, self.child_goal.cancel_goal_async(), 8.0, 'Child cancel')
                except Exception:
                    pass
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
            else:
                goal_handle.abort()
            result.message = str(error)
            self.get_logger().error(result.message)
        finally:
            self.child_goal = None
            self.allow_square_reset = False
            self.square_busy = False
        return result


def main(args=None):
    rclpy.init(args=args)
    node = DrawingNode()
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
