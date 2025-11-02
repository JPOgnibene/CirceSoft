from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os, tempfile
import xacro

def generate_launch_description():
    pkg_share = get_package_share_directory('my_diffbot_sim')

    # Expand Xacro -> URDF
    xacro_file = os.path.join(pkg_share, 'urdf', 'diffbot.urdf.xacro')
    urdf_xml = xacro.process_file(xacro_file).toxml()
    tmp_urdf = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.urdf')
    tmp_urdf.write(urdf_xml); tmp_urdf.flush()

    # Read world and inject absolute texture path (robust in VMs)
    world_tmpl = os.path.join(pkg_share, 'world', 'football_field.sdf')
    with open(world_tmpl, 'r') as f:
        world_text = f.read()
    # Absolute path to your Desktop texture
    texture_abs = '/home/vboxuser/Desktop/football_field.png'
    world_text = world_text.replace('ALBEDO_PATH', f'file://{texture_abs}')
    tmp_world = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sdf')
    tmp_world.write(world_text); tmp_world.flush()

    return LaunchDescription([
        ExecuteProcess(cmd=['gz', 'sim', '-s', '-r', tmp_world.name], output='screen'),
        ExecuteProcess(cmd=['ros2', 'run', 'ros_gz_sim', 'create',
                            '-name', 'diffbot', '-x', '0', '-y', '0', '-z', '0.05',
                            '-file', tmp_urdf.name], output='screen'),

        Node(package='robot_state_publisher', executable='robot_state_publisher',
             name='robot_state_publisher', parameters=[{'robot_description': urdf_xml}]),

        Node(package='ros_gz_bridge', executable='parameter_bridge', name='ros_gz_bridge',
             arguments=['/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',
                        '/odom@nav_msgs/msg/Odometry@gz.msgs.Odometry'],
             output='screen'),

        # ✅ Run the brain as a Python module (no libexec needed)
        ExecuteProcess(
            cmd=['python3', '-m', 'my_diffbot_sim.brain_ws_follower'],
            output='screen'
        ),
    ])
