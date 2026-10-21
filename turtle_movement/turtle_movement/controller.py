"""State-pattern controller; independent of ROS so it can be tested locally."""
import math


def wrap_angle(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


def limit(value, maximum):
    return max(-maximum, min(maximum, value))


class RotateToTarget:
    name = 'ROTATE_TO_TARGET'

    def step(self, controller, pose, max_linear, max_angular):
        distance, heading = controller.errors(pose)
        if distance <= controller.position_tolerance:
            controller.state = AlignFinalYaw()
            return 0.0, 0.0
        if abs(heading) <= 0.015:
            controller.state = DriveToTarget()
            return 0.0, 0.0
        return 0.0, limit(4.0 * heading, max_angular)


class DriveToTarget:
    name = 'DRIVE_TO_TARGET'

    def step(self, controller, pose, max_linear, max_angular):
        distance, heading = controller.errors(pose)
        if distance <= controller.position_tolerance:
            controller.state = AlignFinalYaw()
            return 0.0, 0.0
        if abs(heading) > 0.3:
            controller.state = RotateToTarget()
            return 0.0, 0.0
        return min(1.5 * distance, max_linear), limit(4.0 * heading, max_angular)


class AlignFinalYaw:
    name = 'ALIGN_FINAL_YAW'

    def step(self, controller, pose, max_linear, max_angular):
        error = wrap_angle(controller.target_yaw - pose[2])
        if abs(error) <= controller.yaw_tolerance:
            controller.state = Finished()
            return 0.0, 0.0
        return 0.0, limit(4.0 * error, max_angular)


class Finished:
    name = 'DONE'

    def step(self, controller, pose, max_linear, max_angular):
        return 0.0, 0.0


class PoseController:
    position_tolerance = 0.015
    yaw_tolerance = 0.01

    def __init__(self, x, y, yaw):
        self.target_x, self.target_y, self.target_yaw = x, y, yaw
        self.state = RotateToTarget()

    def errors(self, pose):
        dx = self.target_x - pose[0]
        dy = self.target_y - pose[1]
        return math.hypot(dx, dy), wrap_angle(math.atan2(dy, dx) - pose[2])

    def command(self, pose, max_linear, max_angular):
        return self.state.step(self, pose, max_linear, max_angular)

    @property
    def done(self):
        return isinstance(self.state, Finished)
