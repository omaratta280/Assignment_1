from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    default_config = str(Path(get_package_share_directory('turtle_movement')) / 'config' / 'speeds.yaml')
    return LaunchDescription([
        DeclareLaunchArgument('start_servers', default_value='true'),
        DeclareLaunchArgument('params_file', default_value=default_config),
        Node(package='turtlesim', executable='turtlesim_node', name='turtlesim', output='screen'),
        Node(package='turtle_movement', executable='movement_node', name='movement_node',
             parameters=[LaunchConfiguration('params_file')], output='screen',
             condition=IfCondition(LaunchConfiguration('start_servers'))),
        Node(package='turtle_drawing', executable='drawing_node', name='drawing_node', output='screen',
             condition=IfCondition(LaunchConfiguration('start_servers'))),
    ])
