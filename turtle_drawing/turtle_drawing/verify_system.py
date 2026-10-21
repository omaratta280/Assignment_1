"""Optional real ROS integration test client. Run AFTER the full launch."""
import math
import sys
import time

import rclpy
from action_msgs.msg import GoalStatus, GoalStatusArray
from geometry_msgs.msg import Twist
from rcl_interfaces.srv import GetParameters
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from std_srvs.srv import Trigger
from turtlesim.msg import Pose
from turtle_interfaces.action import GoToPose, DrawSquare
from turtle_interfaces.srv import SetSpeedLimits
from turtle_movement.controller import wrap_angle
from .drawing_node import START


class VerifySystem(Node):
    def __init__(self):
        super().__init__('lab1_verifier')
        self.pose = None
        self.goal_ids = set()
        self.commands = []
        self.feedback_count = 0
        self.create_subscription(Pose, '/turtle1/pose', self.on_pose, 10)
        self.create_subscription(Twist, '/turtle1/cmd_vel', self.on_command, 100)
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(GoalStatusArray, '/go_to_pose/_action/status', self.on_status, qos)
        self.reset_client = self.create_client(Trigger, '/reset_turtle')
        self.speed_client = self.create_client(SetSpeedLimits, '/set_speed_limits')
        self.parameter_client = self.create_client(GetParameters, '/movement_node/get_parameters')
        self.move_client = ActionClient(self, GoToPose, '/go_to_pose')
        self.square_client = ActionClient(self, DrawSquare, '/draw_square')
        self.active_handle = None

    def on_pose(self, message):
        self.pose = message

    def on_command(self, message):
        self.commands.append((message.linear.x, message.angular.z))

    def on_status(self, message):
        self.goal_ids.update(bytes(s.goal_info.goal_id.uuid) for s in message.status_list)

    def on_feedback(self, message):
        self.feedback_count += 1

    def pump(self, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=min(0.05, max(0.0, deadline-time.monotonic())))

    def wait(self, future, seconds=15.0):
        rclpy.spin_until_future_complete(self, future, timeout_sec=seconds)
        if not future.done():
            raise TimeoutError('ROS response timed out. Check the launch terminal.')
        if future.exception() is not None:
            raise future.exception()
        return future.result()

    def speed(self, linear, angular):
        return self.wait(self.speed_client.call_async(SetSpeedLimits.Request(
            max_linear_speed=linear, max_angular_speed=angular)))

    def parameters(self):
        response = self.wait(self.parameter_client.call_async(GetParameters.Request(
            names=['max_linear_speed', 'max_angular_speed'])))
        return [value.double_value for value in response.values]

    def reset(self):
        self.pump(0.3)
        reply = self.wait(self.reset_client.call_async(Trigger.Request()))
        assert reply.success, reply.message
        self.pump(0.2)
        self.check_pose(START, START, 0.0)

    def check_pose(self, x, y, yaw):
        assert self.pose is not None, 'No live turtle pose'
        distance = math.hypot(self.pose.x-x, self.pose.y-y)
        angle = abs(wrap_angle(self.pose.theta-yaw))
        assert distance <= 0.1, f'Position error: {distance:.4f}'
        assert angle <= 0.05, f'Heading error: {angle:.4f}'

    def start(self, client, goal):
        self.feedback_count = 0
        handle = self.wait(client.send_goal_async(goal, feedback_callback=self.on_feedback))
        assert handle.accepted, 'Action goal unexpectedly rejected'
        self.active_handle = handle
        return handle

    def finish(self, handle, seconds=180.0):
        reply = self.wait(handle.get_result_async(), seconds)
        self.active_handle = None
        assert reply.status == GoalStatus.STATUS_SUCCEEDED, reply.result.message
        assert reply.result.success, reply.result.message
        self.pump(0.2)
        assert self.feedback_count > 0, 'No action feedback observed'
        return reply

    @staticmethod
    def target(x, y, yaw):
        goal = GoToPose.Goal()
        goal.target.x, goal.target.y, goal.target.yaw = x, y, yaw
        return goal

    def run_checks(self):
        for client in (self.reset_client, self.speed_client, self.parameter_client):
            assert client.wait_for_service(timeout_sec=15.0), 'Required service missing'
        assert self.move_client.wait_for_server(timeout_sec=15.0), 'goToPose missing'
        assert self.square_client.wait_for_server(timeout_sec=15.0), 'drawSquare missing'
        self.pump(0.5)
        assert self.pose is not None, 'Turtlesim pose missing'
        print('PASS 1: Both actions, all test services and live pose are available.', flush=True)

        self.reset()
        self.reset()
        print('PASS 2: Reset twice returns to the original pose.', flush=True)

        assert self.speed(2.0, 2.0).success
        self.finish(self.start(self.move_client, self.target(8.0, 5.5, math.pi/2)))
        self.check_pose(8.0, 5.5, math.pi/2)
        print('PASS 3: Movement reaches position/yaw with feedback and success.', flush=True)

        before = self.parameters()
        assert not self.speed(-1.0, 1.0).success, 'Negative speed accepted'
        assert self.parameters() == before, 'Rejected update changed parameters'
        assert not self.speed(1.0, 0.0).success, 'Zero speed accepted'
        assert self.parameters() == before, 'Rejected update changed parameters'
        print('PASS 4: Invalid speed service requests are rejected atomically.', flush=True)

        handle = self.start(self.move_client, self.target(2.5, 8.0, 0.0))
        result_future = handle.get_result_async()
        self.pump(0.5)
        assert not result_future.done(), 'Movement finished before live speed test'
        assert self.speed(0.6, 1.0).success
        assert self.parameters() == [0.6, 1.0], 'Speed service did not update ROS parameters'
        self.pump(0.2)
        self.commands.clear()
        self.pump(0.7)
        assert self.commands, 'No velocity commands during live speed test'
        assert all(abs(v) <= 0.60001 and abs(w) <= 1.00001 for v,w in self.commands), 'Live limits exceeded'
        reply = self.wait(result_future, 180.0)
        self.active_handle = None
        assert reply.status == GoalStatus.STATUS_SUCCEEDED and reply.result.success, reply.result.message
        self.pump(0.3)
        self.check_pose(2.5, 8.0, 0.0)
        assert self.speed(2.0, 2.0).success
        print('PASS 5: Speed changes during an active goal; new command limits respected.', flush=True)

        invalid = self.wait(self.move_client.send_goal_async(self.target(20.0, 5.0, 0.0)))
        assert not invalid.accepted, 'Out-of-window goal accepted'
        print('PASS 6: Out-of-window target rejected.', flush=True)

        for run, length in enumerate((2.0, 3.0), 1):
            self.pump(0.3)
            previous_ids = set(self.goal_ids)
            self.finish(self.start(self.square_client, DrawSquare.Goal(side_length=length)))
            self.check_pose(START, START, 0.0)
            self.pump(0.3)
            new_count = len(self.goal_ids - previous_ids)
            assert new_count == 4, f'Square run {run}: observed {new_count} new movement goals, expected 4'
            print(f'PASS {6+run}: Square run {run} completed using exactly four new movement goals.', flush=True)

        invalid_square = self.wait(self.square_client.send_goal_async(DrawSquare.Goal(side_length=8.0)))
        assert not invalid_square.accepted, 'Oversized square accepted'
        self.reset()
        print('PASS 9: Invalid square rejected; final reset succeeded.', flush=True)
        print('ALL AUTOMATIC CHECKS PASSED. Also visually inspect clean resets/right-angle squares and record/replay the rosbag.', flush=True)


def main(args=None):
    rclpy.init(args=args)
    node = VerifySystem()
    failed = False
    try:
        node.run_checks()
    except (Exception, KeyboardInterrupt) as error:
        failed = True
        print(f'FAIL: {type(error).__name__}: {error}', file=sys.stderr, flush=True)
        if node.active_handle is not None:
            try:
                node.wait(node.active_handle.cancel_goal_async(), 5.0)
            except Exception:
                pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    if failed:
        raise SystemExit(1)
