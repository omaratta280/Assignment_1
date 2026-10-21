from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    config = str(Path(get_package_share_directory('turtle_movement')) / 'config' / 'speeds.yaml')
    return LaunchDescription([
        Node(package='turtlesim', executable='turtlesim_node', name='turtlesim', output='screen'),
        Node(package='turtle_movement', executable='movement_node', name='movement_node',
             parameters=[config], output='screen'),
    ])
