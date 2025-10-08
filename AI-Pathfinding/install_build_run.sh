#!/usr/bin/env bash
set -euo pipefail
WS="${1:-$HOME/sim_ws}"
sudo apt update
sudo apt install -y curl wget gnupg lsb-release software-properties-common
# ROS 2 Jazzy
if ! [ -f /usr/share/keyrings/ros-archive-keyring.gpg ]; then
  sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
fi
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/ros2.list >/dev/null
sudo apt update
sudo apt install -y ros-jazzy-desktop ros-jazzy-xacro ros-jazzy-robot-state-publisher ros-jazzy-joint-state-publisher
echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc || true
source /opt/ros/jazzy/setup.bash
# Gazebo + bridge
if ! [ -f /usr/share/keyrings/gazebo-archive-keyring.gpg ]; then
  sudo wget https://packages.osrfoundation.org/gazebo.gpg -O /usr/share/keyrings/gazebo-archive-keyring.gpg
fi
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/gazebo-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(. /etc/os-release; echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/gazebo-stable.list >/dev/null
sudo apt update
sudo apt install -y gz-harmonic ros-jazzy-ros-gz ros-jazzy-ros-gz-bridge ros-jazzy-ros-gz-sim
# build tools
sudo add-apt-repository -y universe || true
sudo apt update
sudo apt install -y python3-colcon-common-extensions python3-rosdep python3-vcstool build-essential unzip
sudo rosdep init || true
rosdep update
# workspace
mkdir -p "$WS/src"
unzip -o my_diffbot_sim_football.zip -d "$WS/src" >/dev/null
cd "$WS"
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 launch my_diffbot_sim sim.launch.py
