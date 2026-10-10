cmake_minimum_required(VERSION 3.0.2)
project(second_coursework)

find_package(catkin REQUIRED COMPONENTS
  rospy
  std_msgs
  geometry_msgs
  sensor_msgs
  actionlib
  actionlib_msgs
  message_generation
)

add_action_files(
  DIRECTORY action
  FILES TidyUp.action
)

generate_messages(
  DEPENDENCIES std_msgs actionlib_msgs
)

catkin_package(
  CATKIN_DEPENDS rospy std_msgs geometry_msgs sensor_msgs actionlib actionlib_msgs message_runtime
)
