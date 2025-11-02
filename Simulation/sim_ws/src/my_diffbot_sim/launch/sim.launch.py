from launch import LaunchDescription
from launch.actions import ExecuteProcess, SetEnvironmentVariable
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os, tempfile
import xacro
def generate_launch_description():
    pkg_share = get_package_share_directory('my_diffbot_sim')
    world_file = os.path.join(pkg_share, 'world', 'football_field.sdf')
    xacro_file = os.path.join(pkg_share, 'urdf', 'diffbot.urdf.xacro')
    urdf_xml = xacro.process_file(xacro_file).toxml()
    tmp = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.urdf')
    tmp.write(urdf_xml); tmp.flush()
    set_res = SetEnvironmentVariable(name='GZ_SIM_RESOURCE_PATH', value=pkg_share)
    return LaunchDescription([
        set_res,
        ExecuteProcess(cmd=['gz', 'sim', world_file], output='screen'),
        ExecuteProcess(cmd=['ros2', 'run', 'ros_gz_sim', 'create',
                            '-name', 'diffbot', '-x', '0', '-y', '0', '-z', '0.05',
                            '-file', tmp.name], output='screen'),
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             name='robot_state_publisher', parameters=[{'robot_description': urdf_xml}]),
        Node(package='ros_gz_bridge', executable='parameter_bridge', name='ros_gz_bridge',
             arguments=['/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',
                        '/odom@nav_msgs/msg/Odometry@gz.msgs.Odometry'], output='screen'),
    ])