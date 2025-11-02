cd ~/sim_ws
rm -rf build install log
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
export GZ_RENDER_ENGINE=ogre
export GZ_SIM_RENDER_ENGINE=ogre
ros2 launch my_diffbot_sim sim_with_brain.launch.py

