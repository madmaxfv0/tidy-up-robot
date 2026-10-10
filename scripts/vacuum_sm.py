#!/usr/bin/env python3
import rospy
import smach
from smach_ros import SimpleActionState
from smach import CBState
from geometry_msgs.msg import Twist
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from std_msgs.msg import String
from tf.transformations import quaternion_from_euler

class RandomMove(smach.State):
    def __init__(self):
        smach.State.__init__(self, outcomes=['dirty','obstacle','battery_low'])
        self.vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=1)
        self.event = None
        rospy.Subscriber('/vacuum_event', String, self._cb)

    def _cb(self, msg):
        self.event = msg.data

    def execute(self, userdata):
        self.event = None
        vel = Twist()
        vel.linear.x = 0.2
        vel.angular.z = 0.3
        for _ in range(10):
            if self.event:
                vel.linear.x = 0.0
                vel.angular.z = 0.0
                self.vel_pub.publish(vel)
                return self.event
            self.vel_pub.publish(vel)
            rospy.sleep(0.5)
        return 'dirty'

class CleanDirt(smach.State):
    def __init__(self):
        smach.State.__init__(self, outcomes=['done'])
    def execute(self, userdata):
        rospy.loginfo("Cleaning dirt...")
        rospy.sleep(2)
        return 'done'

class AvoidObstacle(smach.State):
    def __init__(self):
        smach.State.__init__(self, outcomes=['done'])
        self.vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=1)
    def execute(self, userdata):
        rospy.loginfo("Avoiding obstacle...")
        vel = Twist()
        vel.linear.x = -0.1
        vel.angular.z = 0.5
        self.vel_pub.publish(vel)
        rospy.sleep(2)
        return 'done'

def make_charging_goal(userdata, goal):
    g = MoveBaseGoal()
    g.target_pose.header.frame_id = 'map'
    g.target_pose.header.stamp = rospy.Time.now()
    g.target_pose.pose.position.x = 6.5
    g.target_pose.pose.position.y = 5.28
    q = quaternion_from_euler(0, 0, 0)
    g.target_pose.pose.orientation.x = q[0]
    g.target_pose.pose.orientation.y = q[1]
    g.target_pose.pose.orientation.z = q[2]
    g.target_pose.pose.orientation.w = q[3]
    return g

if __name__ == '__main__':
    rospy.init_node('vacuum_sm')
    sm = smach.StateMachine(outcomes=['shutdown'])
    with sm:
        smach.StateMachine.add('RANDOM_MOVE', RandomMove(),
            transitions={'dirty':'CLEAN', 'obstacle':'AVOID',
                         'battery_low':'GO_CHARGE'})
        smach.StateMachine.add('CLEAN', CleanDirt(),
            transitions={'done':'RANDOM_MOVE'})
        smach.StateMachine.add('AVOID', AvoidObstacle(),
            transitions={'done':'RANDOM_MOVE'})
        smach.StateMachine.add('GO_CHARGE',
            SimpleActionState('move_base', MoveBaseAction,
                goal_cb=make_charging_goal),
            transitions={'succeeded':'RANDOM_MOVE',
                         'preempted':'shutdown', 'aborted':'RANDOM_MOVE'})
    sm.execute()
