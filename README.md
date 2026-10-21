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

## Finish the checks and prepare the submission

On the Ubuntu computer, run:

```bash
cd ~/assignment_1
bash finish_assignment.sh
```

This builds the project, runs the nine ROS checks, records and replays the rosbag,
then checks a fresh local build. If they pass, it creates a `github_upload` folder
with the source packages, test logs and real bag files. The terminal prints its path.

To include the phone video, give its path after the command:

```bash
bash finish_assignment.sh "/home/omaratta/Videos/demo.mp4"
```

Replace the example with the path to the actual video. The video is optional.
Read `FINISH.txt` for the final upload steps. These real ROS checks still need to
run on the Ubuntu computer; the results below are only filled in after they pass.

## Build and run

We use ROS 2 Humble. The commands below use a folder called `assignment_1` in the Home folder.

If the extra packages are missing, install them:

```bash
sudo apt update
sudo apt install ros-humble-turtlesim python3-colcon-common-extensions ros-humble-ros2bag ros-humble-rosbag2-storage-default-plugins
```

Build the project and start it:

```bash
cd ~/assignment_1
bash build.sh
bash run.sh
```

Keep this terminal open. The turtle window should appear.

In each new terminal, run these two lines before using the project:

```bash
source /opt/ros/humble/setup.bash
source ~/assignment_1/install/setup.bash
```

The main launch command is:

```bash
ros2 launch turtle_drawing lab1.launch.py
```

Use `bash run.sh` or the launch command. Run only one copy of the full system at a time.

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

The starting values are saved in `src/turtle_movement/config/speeds.yaml`. After changing this file, build and run the project again. Another YAML file can also be used:

```bash
ros2 launch turtle_drawing lab1.launch.py params_file:=/absolute/path/speeds.yaml
```

## State pattern

We used the State pattern in `turtle_movement/controller.py` to split the movement into four parts:

- `RotateToTarget`: turn towards the point.
- `DriveToTarget`: move towards the point.
- `AlignFinalYaw`: turn to the requested final direction.
- `Finished`: stop the turtle.

`PoseController` keeps the current state and calls its `step` method. Each state decides when to move to the next one. This keeps the movement code easier to read and makes each part easier to check.

## Testing

The four Python controller tests pass. They check movement in different directions, turning, speed limits and squares. These tests calculate the movement without running turtlesim.

```bash
PYTHONPATH=src/turtle_movement python3 -m unittest discover -s src/turtle_movement/test -v
```

After building, the same tests can also be run with colcon:

```bash
sudo apt install python3-pytest
colcon test --packages-select turtle_movement
colcon test-result --verbose
```

<!-- REQUIRED_TESTS_START -->
The turtle has also been run and was seen drawing lines, drawing a square and returning to the start. The final result from the full automatic test still needs to be checked.
<!-- REQUIRED_TESTS_END -->

<!-- CLEAN_BUILD_START -->
The fresh local build still needs to be checked on the Ubuntu computer.
<!-- CLEAN_BUILD_END -->

With the full launch running, use a second terminal:

```bash
ros2 run turtle_drawing verify_system
```

A successful run prints nine `PASS` lines and ends with `ALL AUTOMATIC CHECKS PASSED`. Also look at the turtle window to check the shape and the reset. The steps for testing each part are in `TESTING.md`.

## Rosbag

A rosbag saves ROS messages so they can be played back later. For this project, we record the movement commands and the turtle's position while it draws a square.

After building the ZIP version of the project, run:

```bash
cd ~/assignment_1
bash rosbag_bonus.sh
```

This script starts the project, runs the nine ROS checks, records a square and plays the commands back in a fresh turtle window. It checks that the bag has messages and that the turtle visits the four corners again. Watch the square as well.

If it succeeds, it prints `ROSBAG RECORDING AND PLAYBACK PASSED`. It saves the bag under `src/turtle_drawing/bags/square_run_<timestamp>/`, fills in the results below and makes `assignment_1_with_rosbag.zip`.

Keep `metadata.yaml` and all the `.db3` files together. If the script fails, read the log files in the folder it prints. The manual recording and playback commands are in `TESTING.md`.

<!-- ROSBAG_EVIDENCE_START -->
- Recording script: still needs a real run on the ROS computer.
- Recording: not done yet.
- Bag folder: add after recording.
- Pose message count: add after recording.
- Movement command count: add after recording.
- Playback result: add after playback.
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
| Rosbag bonus | Record and replay the square, then add the bag and results |

## GitHub submission

Upload the three package folders, `README.md`, `TESTING.md` and `.gitignore`. Include the recorded bag inside the drawing package.

The repository should look like this:

```text
turtle_interfaces/
turtle_movement/
turtle_drawing/
README.md
TESTING.md
.gitignore
```

Do not upload `build`, `install`, `log` or the workspace ZIP.

For the clean build check, clone the repository into the `src` folder of a new workspace. From that workspace folder, run:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 launch turtle_drawing lab1.launch.py
```

In this layout, use the normal colcon and launch commands. The `build.sh`, `run.sh` and `rosbag_bonus.sh` scripts belong to the ZIP version. The manual commands in `TESTING.md` can also be used with a cloned repository after changing the workspace path.

Submit the repository link once for the whole team:
https://forms.gle/LHsLkTmFxT3c2Hs66

## References

- Lab 1 assignment sheet.
- ROS 2 Humble tutorials: https://docs.ros.org/en/humble/Tutorials.html
- ROS actions: https://docs.ros.org/en/humble/Tutorials/Intermediate/Writing-an-Action-Server-Client/Py.html
- Rosbag: https://github.com/ros2/rosbag2/tree/humble
- State pattern: https://refactoring.guru/design-patterns/state
