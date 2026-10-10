#!/usr/bin/env python3
# coding=utf-8
"""Tidy-up action server using a SMACH state machine."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rospy
import smach
from smach import CBState
from smach_ros import SimpleActionState
import actionlib
from move_base_msgs.msg import MoveBaseAction
from second_coursework.msg import (TidyUpAction, TidyUpFeedback, TidyUpResult)
from states import (NavigateToRoom, SearchRoom, DeliverAndReturn,
                    make_goal, speak)


class TidyRoomServer:
    def __init__(self):
        self.server = actionlib.SimpleActionServer(
            '/tidy_room', TidyUpAction, self.execute_cb, False)
        self.server.start()
        rospy.loginfo('TidyRoom action server started.')

    @staticmethod
    def nav_goal_cb(userdata, goal):
        return make_goal(userdata.nav_target)

    @staticmethod
    @smach.cb_interface(input_keys=['target_room'], outcomes=['done'])
    def announce_cb(userdata):
        rospy.sleep(1.0)
        speak('I have arrived at the ' + userdata.target_room)
        rospy.sleep(2.0)
        return 'done'

    @staticmethod
    @smach.cb_interface(input_keys=['target_room'], outcomes=['done'])
    def speak_tidying_cb(userdata):
        speak('I am tidying the ' + userdata.target_room)
        rospy.sleep(2.0)
        return 'done'

    def make_feedback_cb(self):
        server = self.server

        @smach.cb_interface(
            input_keys=['detected_obj', 'dest_room'], outcomes=['done'])
        def feedback_cb(userdata):
            fb = TidyUpFeedback()
            fb.object = userdata.detected_obj
            fb.room = userdata.dest_room
            server.publish_feedback(fb)
            rospy.loginfo('Feedback: %s -> %s', fb.object, fb.room)
            return 'done'
        return feedback_cb

    def execute_cb(self, goal):
        rospy.loginfo('Goal received: tidy "%s"', goal.room)
        sm = smach.StateMachine(outcomes=['finished', 'error'])
        sm.userdata.target_room = goal.room
        sm.userdata.nav_target = goal.room
        sm.userdata.objects_done = []
        sm.userdata.rooms_done = []
        sm.userdata.detected_obj = ''
        sm.userdata.dest_room = ''

        with sm:
            smach.StateMachine.add('NAV_TO_ROOM',
                SimpleActionState('move_base', MoveBaseAction,
                    goal_cb=self.nav_goal_cb,
                    input_keys=['nav_target']),
                transitions={'succeeded': 'ANNOUNCE',
                             'preempted': 'error',
                             'aborted':   'error'})
            smach.StateMachine.add('ANNOUNCE',
                CBState(self.announce_cb),
                transitions={'done': 'SEARCH'})
            smach.StateMachine.add('SEARCH', SearchRoom(),
                transitions={'found_object':  'FEEDBACK',
                             'person_seen':   'SPEAK_TIDY',
                             'keep_searching':'SEARCH',
                             'tidying_done':  'finished'})
            smach.StateMachine.add('SPEAK_TIDY',
                CBState(self.speak_tidying_cb),
                transitions={'done': 'SEARCH'})
            smach.StateMachine.add('FEEDBACK',
                CBState(self.make_feedback_cb()),
                transitions={'done': 'DELIVER'})
            smach.StateMachine.add('DELIVER', DeliverAndReturn(),
                transitions={'delivered': 'SEARCH'})

        outcome = sm.execute()
        result = TidyUpResult()
        result.objects = list(sm.userdata.objects_done)
        result.rooms = list(sm.userdata.rooms_done)
        if outcome == 'finished':
            self.server.set_succeeded(result)
        else:
            self.server.set_aborted(result)


if __name__ == '__main__':
    rospy.init_node('tidy_server')
    TidyRoomServer()
    rospy.spin()
