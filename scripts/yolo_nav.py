#!/usr/bin/env python3
import rospy
import actionlib
from std_msgs.msg import String
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from tf.transformations import quaternion_from_euler

TARGETS = {
    'book':       (2.5, 8.5),
    'cell phone': (10.5, 8.5),
    'bottle':     (6.5, 3.0),
}

class YOLONav:
    def __init__(self):
        self.client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
        self.client.wait_for_server()
        rospy.Subscriber('/yolo_detections', String, self.det_cb)
        rospy.loginfo("YOLONav ready. Waiting for detections...")

    def nav_to(self, x, y):
        g = MoveBaseGoal()
        g.target_pose.header.frame_id = 'map'
        g.target_pose.header.stamp = rospy.Time.now()
        g.target_pose.pose.position.x = x
        g.target_pose.pose.position.y = y
        q = quaternion_from_euler(0, 0, 0)
        g.target_pose.pose.orientation.x = q[0]
        g.target_pose.pose.orientation.y = q[1]
        g.target_pose.pose.orientation.z = q[2]
        g.target_pose.pose.orientation.w = q[3]
        self.client.send_goal(g)
        self.client.wait_for_result()

    def det_cb(self, msg):
        obj = msg.data
        if obj == 'apple':
            rospy.loginfo("Apple detected! Shutting down.")
            rospy.signal_shutdown("Apple seen")
            return
        if obj in TARGETS:
            x, y = TARGETS[obj]
            rospy.loginfo("Detected %s -> navigating to (%.1f, %.1f)", obj, x, y)
            self.nav_to(x, y)

if __name__ == '__main__':
    rospy.init_node('yolo_nav')
    YOLONav()
    rospy.spin()
