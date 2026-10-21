# Testing

These steps use `~/assignment_1_ws` as the project folder. Run them in order. Use one full launch at a time and wait for each movement to finish before sending the next one.

## First: try the arrow keys

Do this before starting the full project. Open two terminals.

In terminal A:

```bash
source /opt/ros/humble/setup.bash
ros2 run turtlesim turtlesim_node
```

In terminal B:

```bash
source /opt/ros/humble/setup.bash
ros2 run turtlesim turtle_teleop_key
```

Click inside terminal B and keep it selected. Hold the arrow keys: Up moves
forward, Down moves backward, Left turns left and Right turns right. The turtle
should move and leave a line. The keys are read by terminal B.

After the test, press Ctrl+C in both terminals. Then start step 1 below.

## 1. Build

Open the first terminal:

```bash
cd ~/assignment_1_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
```

All three packages should build without errors. If a package is missing, install the packages listed in the README. ROS 2 Humble must already be installed.

## 2. Start the project

In the same terminal:

```bash
source ~/assignment_1_ws/install/setup.bash
ros2 launch turtle_drawing lab1.launch.py
```

The turtle window should open. The terminal should show that the movement and drawing nodes are ready. Keep this terminal open.

## 3. Set up the other terminals

Run these two lines in every new terminal used below:

```bash
source /opt/ros/humble/setup.bash
source ~/assignment_1_ws/install/setup.bash
```

## 4. Run the automatic test

In a second terminal:

```bash
ros2 run turtle_drawing verify_system
```

The turtle will draw some lines, draw two squares and reset. The test also checks the final position and direction, feedback, speed changes and rejected values.

Wait for all nine `PASS` lines and `ALL AUTOMATIC CHECKS PASSED`. It can take a few minutes. Do not send other movement commands during this test.

Look at the turtle window too. The square should have equal sides and right-angle corners. Reset should clear the screen without leaving a connecting line.

If the test prints `FAIL`, check that line and the errors in the first terminal. The steps below can be used to check each part on its own.

## 5. Check the nodes and interfaces

```bash
ros2 node list
ros2 topic list
ros2 service list
ros2 action list -t
ros2 interface show turtle_interfaces/msg/TargetPose
ros2 interface show turtle_interfaces/action/GoToPose
ros2 interface show turtle_interfaces/action/DrawSquare
ros2 interface show turtle_interfaces/srv/SetSpeedLimits
```

The main nodes should be `/turtlesim`, `/movement_node` and `/drawing_node`. The test node only appears while the automatic test is running. Check that the target message has `x`, `y` and `yaw`.

## 6. Test movement

Send one goal at a time. Wait for the result before running the next command.

```bash
ros2 action send_goal /go_to_pose turtle_interfaces/action/GoToPose "{target: {x: 8.0, y: 5.5, yaw: 1.5708}}" --feedback
ros2 topic echo /turtle1/pose --once
ros2 action send_goal /go_to_pose turtle_interfaces/action/GoToPose "{target: {x: 3.0, y: 5.5, yaw: 3.1416}}" --feedback
ros2 action send_goal /go_to_pose turtle_interfaces/action/GoToPose "{target: {x: 3.0, y: 8.0, yaw: 1.5708}}" --feedback
ros2 action send_goal /go_to_pose turtle_interfaces/action/GoToPose "{target: {x: 3.0, y: 2.5, yaw: -1.5708}}" --feedback
ros2 action send_goal /go_to_pose turtle_interfaces/action/GoToPose "{target: {x: 8.0, y: 2.5, yaw: 0.0}}" --feedback
```

Check that the turtle reaches each point and turns to the final direction. The position error should be below `0.1` and the direction error below `0.05` radians. Feedback should appear while it moves.

Check turning in place and moving towards a point behind the turtle:

```bash
ros2 action send_goal /go_to_pose turtle_interfaces/action/GoToPose "{target: {x: 8.0, y: 2.5, yaw: 3.1416}}" --feedback
ros2 action send_goal /go_to_pose turtle_interfaces/action/GoToPose "{target: {x: 9.0, y: 2.5, yaw: 0.0}}" --feedback
```

Try a point outside the window:

```bash
ros2 action send_goal /go_to_pose turtle_interfaces/action/GoToPose "{target: {x: 20.0, y: 5.0, yaw: 0.0}}" --feedback
```

This goal should be rejected.

## 7. Test the speed limits

Read and change the parameters:

```bash
ros2 param list /movement_node
ros2 param get /movement_node max_linear_speed
ros2 param get /movement_node max_angular_speed
ros2 param set /movement_node max_linear_speed 0.5
ros2 param set /movement_node max_angular_speed 0.8
```

Send this goal in the second terminal:

```bash
ros2 action send_goal /go_to_pose turtle_interfaces/action/GoToPose "{target: {x: 2.0, y: 9.0, yaw: 0.0}}" --feedback
```

While the turtle is moving, open a third terminal, run the two setup lines from step 3, then run:

```bash
ros2 param set /movement_node max_linear_speed 1.5
ros2 service call /set_speed_limits turtle_interfaces/srv/SetSpeedLimits "{max_linear_speed: 0.4, max_angular_speed: 0.8}"
ros2 param get /movement_node max_linear_speed
ros2 param get /movement_node max_angular_speed
```

The speed should change during the same movement. The two values should now be `0.4` and `0.8`.

After the movement finishes, try these invalid values:

```bash
ros2 service call /set_speed_limits turtle_interfaces/srv/SetSpeedLimits "{max_linear_speed: -1.0, max_angular_speed: 1.0}"
ros2 service call /set_speed_limits turtle_interfaces/srv/SetSpeedLimits "{max_linear_speed: 1.0, max_angular_speed: 0.0}"
ros2 param set /movement_node max_linear_speed -1.0
ros2 param get /movement_node max_linear_speed
ros2 param get /movement_node max_angular_speed
```

These changes should fail. The old valid values should stay the same. Use decimal numbers such as `1.0` when setting speeds.

Set the normal speeds again:

```bash
ros2 service call /set_speed_limits turtle_interfaces/srv/SetSpeedLimits "{max_linear_speed: 2.0, max_angular_speed: 2.0}"
```

## 8. Test reset

Wait for the turtle to stop, then run:

```bash
ros2 service call /reset_turtle std_srvs/srv/Trigger "{}"
ros2 topic echo /turtle1/pose --once
ros2 service call /reset_turtle std_srvs/srv/Trigger "{}"
```

The screen should clear and the turtle should return to about `(5.5444, 5.5444)` with yaw `0`. There should be no line from the old position to the centre. Both reset calls should work.

## 9. Draw the square twice

Run these one after the other:

```bash
ros2 action send_goal /draw_square turtle_interfaces/action/DrawSquare "{side_length: 3.0}" --feedback
ros2 action send_goal /draw_square turtle_interfaces/action/DrawSquare "{side_length: 3.0}" --feedback
```

Each square should start with a clear screen. Check that the sides look equal and the corners look like 90 degrees.

For each square, the first terminal should show four `SQUARE side N/4` messages and four new `GO_TO_POSE` entries. The movement counter keeps increasing, so count the four new entries for that square.

Try a square that is too large:

```bash
ros2 action send_goal /draw_square turtle_interfaces/action/DrawSquare "{side_length: 8.0}" --feedback
```

It should be rejected.

## 10. Check the YAML values

Stop the first terminal with Ctrl+C. Open this file:

```text
~/assignment_1_ws/src/assignment_1/turtle_movement/config/speeds.yaml
```

Change both speeds to `1.0`, then build and run the project again:

```bash
cd ~/assignment_1_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source ~/assignment_1_ws/install/setup.bash
ros2 launch turtle_drawing lab1.launch.py
```

In a second terminal with the setup lines already run, check:

```bash
ros2 param get /movement_node max_linear_speed
ros2 param get /movement_node max_angular_speed
```

Both should show `1.0`. Put the file values back to `2.0` and build and run again before recording.

## 11. Record the rosbag

### Record manually

Keep the full launch running. In the second terminal, set the speeds and reset:

```bash
ros2 service call /set_speed_limits turtle_interfaces/srv/SetSpeedLimits "{max_linear_speed: 2.0, max_angular_speed: 2.0}"
ros2 service call /reset_turtle std_srvs/srv/Trigger "{}"
```

In a third terminal with the setup lines already run:

```bash
ros2 bag record -s sqlite3 -o ~/assignment_1_ws/src/assignment_1/turtle_drawing/bags/square_run /turtle1/cmd_vel /turtle1/pose
```

Wait until the recorder shows that it has subscribed to both topics. In the second terminal, draw the square:

```bash
ros2 action send_goal /draw_square turtle_interfaces/action/DrawSquare "{side_length: 3.0}" --feedback
```

Wait for the square to finish. Then press Ctrl+C in the recorder terminal so the bag is saved properly.

```bash
ros2 bag info ~/assignment_1_ws/src/assignment_1/turtle_drawing/bags/square_run
```

Check that both topics have more than zero messages. Keep `metadata.yaml` and the `.db3` files together.

If `square_run` already exists, use a new name such as `square_run_2` in the recording and playback commands.

## 12. Play back the manual recording

Stop the full launch with Ctrl+C in the first terminal. Stop any other program that sends movement commands.

Start turtlesim on its own:

```bash
cd ~/assignment_1_ws
source ~/assignment_1_ws/install/setup.bash
ros2 launch turtle_drawing lab1.launch.py start_servers:=false
```

In the second terminal, reset the new simulator:

```bash
ros2 service call /reset std_srvs/srv/Empty "{}"
```

This is turtlesim's normal reset service. It is only used here to prepare for playback. The project's own reset service was checked in step 8.

Play only the saved movement commands:

```bash
ros2 bag play ~/assignment_1_ws/src/assignment_1/turtle_drawing/bags/square_run --topics /turtle1/cmd_vel
```

The turtle should draw about the same square again. It must start from the same position and direction as the recording. Do not play the saved `/turtle1/pose` messages over the new simulator's position messages.

If the turtle needs to be stopped:

```bash
ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0}, angular: {z: 0.0}}"
```

Add the recording date, message counts, bag folder and playback result to the README. Also add a short note or screenshot showing the playback.

## 13. Check before submitting

- Check the three names and IDs in the README.
- Check that the State pattern is explained.
- Save the actual bag inside the drawing package.
- Fill in the recording and playback results after doing the test.
- Upload the source packages, README and testing guide to GitHub.
- Leave out `build`, `install` and `log`.
- Clone the repository into a new workspace and check that it builds and runs.
- Submit the repository link through the assignment form.

## Common problems

| Problem | What to check |
| --- | --- |
| Package or action not found | Build the project and run both setup lines in this terminal |
| Executable not found | Check the build errors and use the correct workspace setup file |
| Turtle window does not open | Use the Ubuntu desktop and check the launch terminal for errors |
| Goal rejected just after starting | Wait for the nodes to be ready and make sure no other goal is running |
| Two turtle windows during normal testing | Stop the older full launch and use one copy |
| Speed change rejected | Use a positive decimal number such as `1.0` |
| Service not ready | Wait for startup and check `ros2 service list` |
| Bag output folder already exists | Choose a new recording folder name |
| Automatic test fails | Read the `FAIL` line and the launch terminal error |
