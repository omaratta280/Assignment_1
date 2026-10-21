"""Person 1: movement action and live speed service/parameters."""
import math
import time

import rclpy
from geometry_msgs.msg import Twist
from rcl_interfaces.msg import SetParametersResult
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.task import Future
from turtlesim.msg import Pose
from turtle_interfaces.action import GoToPose
from turtle_interfaces.srv import SetSpeedLimits
from .controller import PoseController, wrap_angle


class MovementNode(Node):
    def __init__(self):
        super().__init__('movement_node')
        self.group = ReentrantCallbackGroup()
        self.add_on_set_parameters_callback(self.validate_parameters)
        self.declare_parameter('max_linear_speed', 2.0)
        self.declare_parameter('max_angular_speed', 2.0)
        self.pose = None
        self.pose_time = 0.0
        self.busy = False
        self.active_goal = None
        self.controller = None
        self.finished_future = None
        self.started_at = 0.0
        self.goal_count = 0
        self.velocity_publisher = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)
        self.pose_subscription = self.create_subscription(Pose, '/turtle1/pose', self.on_pose, 10)
        self.speed_service = self.create_service(SetSpeedLimits, '/set_speed_limits', self.set_speeds)
        self.action_server = ActionServer(
            self, GoToPose, '/go_to_pose', execute_callback=self.execute_goal,
            goal_callback=self.accept_goal, cancel_callback=self.cancel_goal,
            callback_group=self.group)
        self.control_timer = self.create_timer(1.0 / 30.0, self.control_tick)
        self.get_logger().info('Movement node ready: /go_to_pose and /set_speed_limits')

    def on_pose(self, message):
        self.pose = (message.x, message.y, message.theta)
        self.pose_time = time.monotonic()

    def validate_parameters(self, parameters):
        for parameter in parameters:
            if parameter.name in ('max_linear_speed', 'max_angular_speed'):
                valid = (parameter.type_ == Parameter.Type.DOUBLE
                         and math.isfinite(parameter.value) and parameter.value > 0.0)
                if not valid:
                    return SetParametersResult(
                        successful=False,
                        reason=parameter.name + ' must be a positive finite float')
        return SetParametersResult(successful=True)

    def set_speeds(self, request, response):
        update = self.set_parameters_atomically([
            Parameter('max_linear_speed', value=request.max_linear_speed),
            Parameter('max_angular_speed', value=request.max_angular_speed)])
        response.success = update.successful
        response.message = 'Both speed limits updated.' if update.successful else update.reason
        return response

    def accept_goal(self, request):
        target = request.target
        valid = all(math.isfinite(value) for value in (target.x, target.y, target.yaw))
        inside = 0.2 <= target.x <= 10.8 and 0.2 <= target.y <= 10.8
        if self.busy or self.pose is None or not valid or not inside:
            self.get_logger().warning('Goal rejected: busy, no pose, or invalid target.')
            return GoalResponse.REJECT
        self.busy = True
        return GoalResponse.ACCEPT

    def cancel_goal(self, goal_handle):
        return CancelResponse.ACCEPT

    async def execute_goal(self, goal_handle):
        target = goal_handle.request.target
        self.active_goal = goal_handle
        self.controller = PoseController(target.x, target.y, target.yaw)
        self.finished_future = Future()
        self.started_at = time.monotonic()
        self.goal_count += 1
        self.get_logger().info(
            f'GO_TO_POSE #{self.goal_count}: x={target.x:.3f}, y={target.y:.3f}, yaw={target.yaw:.3f}')
        try:
            status, message = await self.finished_future
            result = GoToPose.Result(success=status == 'success', message=message)
            if status == 'success':
                goal_handle.succeed()
            elif status == 'cancel':
                goal_handle.canceled()
            else:
                goal_handle.abort()
            return result
        finally:
            self.stop_turtle()
            self.active_goal = None
            self.controller = None
            self.finished_future = None
            self.busy = False

    def finish(self, status, message):
        self.stop_turtle()
        if self.finished_future is not None and not self.finished_future.done():
            self.finished_future.set_result((status, message))

    def control_tick(self):
        if self.active_goal is None or self.finished_future.done():
            return
        if self.active_goal.is_cancel_requested:
            self.finish('cancel', 'Movement canceled; turtle stopped.')
            return
        if time.monotonic() - self.started_at > 300.0:
            self.finish('failure', 'Movement exceeded 300 seconds.')
            return
        if self.pose is None or time.monotonic() - self.pose_time > 2.0:
            self.finish('failure', 'Pose updates unavailable or stale.')
            return
        max_linear = self.get_parameter('max_linear_speed').value
        max_angular = self.get_parameter('max_angular_speed').value
        linear, angular = self.controller.command(self.pose, max_linear, max_angular)
        command = Twist()
        command.linear.x, command.angular.z = linear, angular
        self.velocity_publisher.publish(command)
        distance, _ = self.controller.errors(self.pose)
        self.active_goal.publish_feedback(GoToPose.Feedback(
            remaining_distance=distance,
            heading_error=wrap_angle(self.controller.target_yaw - self.pose[2]),
            phase=self.controller.state.name))
        if self.controller.done:
            self.finish('success', 'Target position and final heading reached.')

    def stop_turtle(self):
        self.velocity_publisher.publish(Twist())


def main(args=None):
    rclpy.init(args=args)
    node = MovementNode()
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.stop_turtle()
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
