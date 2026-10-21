from glob import glob
from setuptools import setup

package_name = 'turtle_movement'
setup(
    name=package_name, version='0.1.0', packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
    ],
    install_requires=['setuptools'], zip_safe=True,
    maintainer='Lab Team', maintainer_email='team@example.com',
    description='goToPose action, live speed limits and State-pattern controller.', license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={'console_scripts': ['movement_node = turtle_movement.movement_node:main']},
)
