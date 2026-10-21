import math
import unittest
from turtle_movement.controller import PoseController, wrap_angle


def simulate(start, target, slow_after=None):
    pose = list(start)
    controller = PoseController(*target)
    states = set()
    dt = 1.0/30.0
    for tick in range(12000):
        max_v, max_w = (0.5, 0.8) if slow_after is not None and tick >= slow_after else (2.0, 2.0)
        v, w = controller.command(pose, max_v, max_w)
        states.add(controller.state.name)
        assert 0.0 <= v <= max_v + 1e-12
        assert abs(w) <= max_w + 1e-12
        pose[0] += v*math.cos(pose[2])*dt
        pose[1] += v*math.sin(pose[2])*dt
        pose[2] = wrap_angle(pose[2]+w*dt)
        if controller.done:
            assert math.hypot(target[0]-pose[0], target[1]-pose[1]) <= 0.016
            assert abs(wrap_angle(target[2]-pose[2])) <= 0.011
            assert (v,w) == (0.0,0.0)
            return tuple(pose), states
    raise AssertionError('Controller did not converge')


class ControllerTests(unittest.TestCase):
    def test_directional_goals_and_rotation_only(self):
        for target in [(8.,5.5,math.pi/2), (3.,5.5,math.pi), (5.5,8.,-math.pi/2),
                       (5.5,2.,0.), (2.,2.,3.13), (9.,9.,-3.13), (5.5,5.5,math.pi)]:
            with self.subTest(target=target):
                simulate((5.5,5.5,0.), target)

    def test_live_lower_limits_and_real_state_transitions(self):
        _, states = simulate((5.5,5.5,math.pi), (9.,9.,-1.), slow_after=20)
        self.assertTrue({'ROTATE_TO_TARGET','DRIVE_TO_TARGET','ALIGN_FINAL_YAW','DONE'} <= states)

    def test_four_goal_squares(self):
        c = 5.544444561004639
        for side in (0.2, 2.0, 3.0, 5.0):
            with self.subTest(side=side):
                pose = (c,c,0.)
                for target in [(c+side,c,math.pi/2), (c+side,c+side,math.pi),
                               (c,c+side,-math.pi/2), (c,c,0.)]:
                    pose,_ = simulate(pose, target)
                self.assertLessEqual(math.hypot(pose[0]-c, pose[1]-c), 0.016)

    def test_short_turn_across_pi(self):
        self.assertAlmostEqual(wrap_angle(-math.pi+0.01-(math.pi-0.01)), 0.02)


if __name__ == '__main__':
    unittest.main()
