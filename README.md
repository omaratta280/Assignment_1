# Assignment 1 - ROS 2 and Turtlesim

This project moves the turtle to a point and makes it draw a square. It also has a reset service and two speed limits that can be changed while the turtle is moving.

## Team

| Name | Student ID |
| --- | --- |
| Omar Atta | 9488 |
| Yassin El Sharkawy | 9462 |
| Ezz Eldin Ashraf | 9238 |

## Packages

The project has three packages:

- `turtle_interfaces`: the message, actions and speed service types.
- `turtle_movement`: moves the turtle and controls its speed.
- `turtle_drawing`: resets the turtle and draws the square.

There are two main nodes, `movement_node` and `drawing_node`. The launch file also starts the normal turtlesim node. `verify_system` is a separate program for testing the project.

## Test results

The real ROS test logs and bag files are included inside the drawing package. The results below show the checks completed before this copy was made.

## Build and run

Use Ubuntu with ROS 2 Humble. The repository has the three package folders at its root.
For a new workspace, clone the project like this:

```bash
mkdir -p ~/assignment_1_ws/src
cd ~/assignment_1_ws/src
git clone https://github.com/omaratta280/Assignment_1.git assignment_1
```

If needed, install the extra packages:

```bash
sudo apt update
sudo apt install ros-humble-turtlesim python3-colcon-common-extensions ros-humble-ros2bag ros-humble-rosbag2-storage-default-plugins
```

From the workspace folder, build and start the project:

```bash
cd ~/assignment_1_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 launch turtle_drawing lab1.launch.py
```

Keep that terminal open. In every new terminal, run:

```bash
source /opt/ros/humble/setup.bash
source ~/assignment_1_ws/install/setup.bash
```

The Python controller test command below is run from the repository folder,
`~/assignment_1_ws/src/assignment_1`. Run the colcon test commands from the workspace folder.

## Check the interfaces

The target message has three numbers: `x`, `y` and `yaw`. `yaw` is the final direction of the turtle in radians.

```bash
ros2 interface show turtle_interfaces/msg/TargetPose
ros2 interface show turtle_interfaces/action/GoToPose
ros2 interface show turtle_interfaces/action/DrawSquare
ros2 interface show turtle_interfaces/srv/SetSpeedLimits
```

Check the running nodes and actions:

```bash
ros2 node list
ros2 action list -t
```

The main nodes should be `/turtlesim`, `/movement_node` and `/drawing_node`. The actions should be `/go_to_pose` and `/draw_square`.

## Move to a point

The movement action uses `TargetPose` as its goal. The turtle turns towards the point, moves to it, then turns to the final yaw. It sends feedback while moving and a result when it finishes.

```bash
ros2 action send_goal /go_to_pose turtle_interfaces/action/GoToPose "{target: {x: 8.0, y: 5.5, yaw: 1.5708}}" --feedback
ros2 topic echo /turtle1/pose --once
```

Wait for one goal to finish before sending another. The feedback shows the distance left, the error in the final direction and the current movement state.

The target's `x` and `y` values must be between `0.2` and `10.8` so the turtle stays inside the window.

## Reset the turtle

```bash
ros2 service call /reset_turtle std_srvs/srv/Trigger "{}"
```

The reset service turns the pen off, teleports the turtle back to the centre, clears the screen and turns the pen on again. It uses turtlesim's own services. This avoids drawing a line while the turtle is moved back.

The starting position is about `(5.5444, 5.5444)` and the starting yaw is `0`. Wait for movement to finish before calling reset.

## Draw a square

```bash
ros2 action send_goal /draw_square turtle_interfaces/action/DrawSquare "{side_length: 3.0}" --feedback
```

The square action calls reset first. It then sends four goals to `/go_to_pose`, one for each corner. It waits for each goal to finish before sending the next one. The fourth goal brings the turtle back to the start.

The feedback shows which side is being drawn. A full square should give four new `GO_TO_POSE` entries in the launch terminal. Running the square again should clear the old drawing first.

The side length must be between `0.2` and `5.0`.

## Change the speed

There are two parameters: `max_linear_speed` for moving and `max_angular_speed` for turning. Both start at `2.0`.

```bash
ros2 param list /movement_node
ros2 param get /movement_node max_linear_speed
ros2 param get /movement_node max_angular_speed
ros2 param set /movement_node max_linear_speed 0.5
ros2 param set /movement_node max_angular_speed 0.8
```

The speed service changes both limits together:

```bash
ros2 service call /set_speed_limits turtle_interfaces/srv/SetSpeedLimits "{max_linear_speed: 1.0, max_angular_speed: 1.5}"
```

The movement node reads the limits each time it sends a movement command, so changes work during the same goal. Zero and negative values are rejected. Write speeds as decimal numbers, such as `1.0`.

The starting values are saved in `turtle_movement/config/speeds.yaml`. After changing this file, build and run the project again. Another YAML file can also be used:

```bash
ros2 launch turtle_drawing lab1.launch.py params_file:=/absolute/path/speeds.yaml
```

## State pattern

We used the State pattern in `turtle_movement/turtle_movement/controller.py` to split the movement into four parts:

- `RotateToTarget`: turn towards the point.
- `DriveToTarget`: move towards the point.
- `AlignFinalYaw`: turn to the requested final direction.
- `Finished`: stop the turtle.

`PoseController` keeps the current state and calls its `step` method. Each state decides when to move to the next one. This keeps the movement code easier to read and makes each part easier to check.

## Testing

The four Python controller tests pass. They check movement in different directions, turning, speed limits and squares. These tests calculate the movement without running turtlesim.

```bash
PYTHONPATH=turtle_movement python3 -m unittest discover -s turtle_movement/test -v
```

After building, the same tests can also be run with colcon:

```bash
sudo apt install python3-pytest
colcon test --packages-select turtle_movement
colcon test-result --verbose
```

<!-- REQUIRED_TESTS_START -->
All nine automatic ROS checks passed on 2026-10-21T18:45:57.629617+00:00. The test log is in `turtle_drawing/bags/square_run_20261021T184357_123725Z/required_tests.log`.
<!-- REQUIRED_TESTS_END -->

<!-- CLEAN_BUILD_START -->
A fresh local copy of all three packages built successfully on 2026-10-21T18:46:17.227522+00:00. The log is in `turtle_drawing/bags/square_run_20261021T184357_123725Z/clean_build.log`.
<!-- CLEAN_BUILD_END -->

With the full launch running, use a second terminal:

```bash
ros2 run turtle_drawing verify_system
```

A successful run prints nine `PASS` lines and ends with `ALL AUTOMATIC CHECKS PASSED`. Also look at the turtle window to check the shape and the reset. The steps for testing each part are in `TESTING.md`.

## Rosbag

A rosbag saves the movement commands and turtle position. The recorded files and playback results are included below. Keep metadata.yaml and the .db3 files together. The manual recording and playback commands are in TESTING.md.

[Bag files](turtle_drawing/bags/square_run_20261021T184357_123725Z/bag/),
[ROS test log](turtle_drawing/bags/square_run_20261021T184357_123725Z/required_tests.log),
[playback results](turtle_drawing/bags/square_run_20261021T184357_123725Z/evidence.md),
and [fresh build log](turtle_drawing/bags/square_run_20261021T184357_123725Z/clean_build.log).

<!-- ROSBAG_EVIDENCE_START -->
- Recording checked at: 2026-10-21T18:45:57.629617+00:00
- Real bag: `turtle_drawing/bags/square_run_20261021T184357_123725Z/bag`
- Pose message count: 1406
- Velocity message count: 645
- Recorded duration: 22.48 seconds
- Playback: ros2 bag play exited successfully; only velocity commands replayed.
- Live trajectory: 1547 pose samples, 4/4 corners visited in order.
- Final replay position error: 0.102; yaw error: 0.038 rad.
- Automatic replay tolerances: 0.30 position; 0.15 rad heading.
- Watch the simulator as well to confirm the visible square.
<!-- ROSBAG_EVIDENCE_END -->

## What each part covers

| Requirement | Where it is done |
| --- | --- |
| R1: Run and control turtlesim | Launch file and movement node |
| R2: Custom target message | `TargetPose.msg`, used in `GoToPose.action` |
| R3: Move to a pose | `/go_to_pose` action |
| R4: Reset | `/reset_turtle` service |
| R5: Square using four movement goals | `/draw_square` action |
| R6: Launch everything | `lab1.launch.py` |
| R7: Speed parameters and service | Movement node and `speeds.yaml` |
| R8: Separate packages | Interfaces, movement and drawing packages |
| State pattern bonus | Four state classes in `controller.py` |
| Rosbag bonus | Recorded bag and successful playback results |

## Submission

The repository contains the three source packages and the test notes. The real bag and test logs are inside the drawing package.

Repository: https://github.com/omaratta280/Assignment_1

Before submitting, a teammate should clone the uploaded repository into a new
workspace, build it and follow TESTING.md. The fresh local build noted above was
done before the GitHub upload. Add the actual clone-test result after doing it.

Submit the repository link once for the team through https://forms.gle/LHsLkTmFxT3c2Hs66 .

## References

- Lab 1 assignment sheet.
- ROS 2 Humble tutorials: https://docs.ros.org/en/humble/Tutorials.html
- ROS actions: https://docs.ros.org/en/humble/Tutorials/Intermediate/Writing-an-Action-Server-Client/Py.html
- Rosbag: https://github.com/ros2/rosbag2/tree/humble
- State pattern: https://refactoring.guru/design-patterns/state
