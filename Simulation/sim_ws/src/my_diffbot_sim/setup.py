from setuptools import setup, find_packages
from glob import glob

package_name = 'my_diffbot_sim'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(include=[package_name]),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.py') + glob('Launch/*.py')),
        ('share/' + package_name + '/urdf',   glob('urdf/*.xacro')),
        ('share/' + package_name + '/world',  glob('world/*.sdf')),
        ('share/' + package_name + '/media',  glob('media/*.*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='You',
    maintainer_email='you@example.com',
    description='Diff-drive robot with WebSocket brain + Gazebo world',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'brain_ws_follower = my_diffbot_sim.brain_ws_follower:main',
        ],
    },
)
