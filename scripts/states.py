#!/usr/bin/env python3
# coding=utf-8
"""SMACH state classes for the tidy-up robot."""
import rospy
import smach
import actionlib
import subprocess
from geometry_msgs.msg import Twist
from std_msgs.msg import String
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from tf.transformations import quaternion_from_euler

# ── Room coordinates (CALIBRATE THESE AT THE LAB) ─────────────
# Robot initial pose from test script: x=6.52 y=5.28 (Room E)
ROOM_COORDS = {
    'kitchen':     (2.5, 8.5),
    'garage':      (6.5, 8.5),
    'bedroom-1':   (10.5, 8.5),
    'bedroom-2':   (2.5, 3.0),
    'living-room': (6.5, 3.0),
    'bathroom':    (10.5, 3.0),
}

# ── Which objects belong in each room ──────────────────────────
ROOM_OBJECTS = {
    'kitchen':     {'microwave','refrigerator','bottle','sink','fork',
                    'banana','sandwich','chair'},
    'garage':      {'bicycle','car','sports ball','skateboard','motorbike'},
    'bedroom-1':   {'bottle','laptop','suitcase','tvmonitor','sports ball',
                    'skateboard','chair','bed'},
    'bedroom-2':   {'bottle','laptop','handbag','tvmonitor','sports ball',
                    'skateboard','chair','bed'},
    'living-room': {'tvmonitor','remote','book','clock','chair'},
    'bathroom':    {'toothbrush','toilet','sink'},
}


def make_goal(room):
    """Build a MoveBaseGoal for the given room name."""
    x, y = ROOM_COORDS[room]
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
    return g


def find_destination(obj, current_room):
    """Return a room where obj belongs (other than current_room)."""
    for room, objs in ROOM_OBJECTS.items():
        if obj in objs and room != current_room:
            return room
    return None


# ── TTS: try sound_play first, fall back to espeak ─────────────
_sound_client = None
_tts_method = None

def speak(text):
    """Speak text using sound_play (lecture method). Falls back to espeak."""
    global _sound_client, _tts_method
    rospy.loginfo('TTS: %s', text)
    if _tts_method == 'espeak':
        subprocess.Popen(['espeak', '-s', '150', text])
        return
    if _sound_client is None:
        try:
            from sound_play.libsoundplay import SoundClient
            _sound_client = SoundClient(blocking=False)
            rospy.sleep(1)
            _tts_method = 'sound_play'
        except Exception:
            _tts_method = 'espeak'
            subprocess.Popen(['espeak', '-s', '150', text])
            return
    _sound_client.say(text)


# ================================================================
#  STATE: Navigate to a room using move_base
# ================================================================
class NavigateToRoom(smach.State):
    def __init__(self):
        smach.State.__init__(self,
            outcomes=['succeeded', 'aborted'],
            input_keys=['target_room'])
        self.client = actionlib.SimpleActionClient('move_base', MoveBaseAction)

    def execute(self, userdata):
        self.client.wait_for_server(rospy.Duration(15))
        goal = make_goal(userdata.target_room)
        self.client.send_goal(goal)
        finished = self.client.wait_for_result(rospy.Duration(120))
        if finished and self.client.get_state() == actionlib.GoalStatus.SUCCEEDED:
            return 'succeeded'
        return 'aborted'


# ================================================================
#  STATE: Search the room - move around and check YOLO detections
# ================================================================
class SearchRoom(smach.State):
    def __init__(self):
        smach.State.__init__(self,
            outcomes=['found_object', 'person_seen', 'keep_searching', 'tidying_done'],
            input_keys=['target_room', 'objects_done', 'rooms_done'],
            output_keys=['detected_obj', 'dest_room'])
        self.vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=1)
        self.latest = None
        rospy.Subscriber('/yolo_detections', String, self._det_cb)
        self.search_step = 0

    def _det_cb(self, msg):
        self.latest = msg.data

    def execute(self, userdata):
        if len(userdata.objects_done) >= 2:
            return 'tidying_done'

        # Move within the room (linear + angular = NOT pure rotation)
        vel = Twist()
        patterns = [(0.15, 0.4), (0.2, -0.3), (0.18, 0.0), (0.1, 0.5)]
        lx, az = patterns[self.search_step % len(patterns)]
        vel.linear.x = lx
        vel.angular.z = az
        self.vel_pub.publish(vel)
        rospy.sleep(2.0)

        # Stop and allow detection
        vel.linear.x = 0.0
        vel.angular.z = 0.0
        self.vel_pub.publish(vel)
        rospy.sleep(1.5)

        self.search_step += 1
        det = self.latest
        self.latest = None

        if det is None:
            return 'keep_searching'

        if det == 'person':
            return 'person_seen'

        # Check if object is misplaced
        if det not in ROOM_OBJECTS.get(userdata.target_room, set()):
            dest = find_destination(det, userdata.target_room)
            if dest:
                userdata.detected_obj = det
                userdata.dest_room = dest
                return 'found_object'

        return 'keep_searching'


# ================================================================
#  STATE: Deliver object to correct room, check person, return
# ================================================================
class DeliverAndReturn(smach.State):
    def __init__(self):
        smach.State.__init__(self,
            outcomes=['delivered'],
            input_keys=['target_room', 'detected_obj', 'dest_room',
                        'objects_done', 'rooms_done'],
            output_keys=['objects_done', 'rooms_done'])
        self.client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
        self.latest = None
        rospy.Subscriber('/yolo_detections', String, self._det_cb)

    def _det_cb(self, msg):
        self.latest = msg.data

    def _nav(self, room):
        self.client.wait_for_server(rospy.Duration(15))
        self.client.send_goal(make_goal(room))
        self.client.wait_for_result(rospy.Duration(120))

    def execute(self, userdata):
        # Navigate to destination room
        self._nav(userdata.dest_room)

        # Person check after arriving at destination (carrying object)
        rospy.sleep(1.5)
        if self.latest == 'person':
            speak('I am taking the {} to {}'.format(
                userdata.detected_obj, userdata.dest_room))
            self.latest = None

        # Record delivery
        ol = list(userdata.objects_done)
        rl = list(userdata.rooms_done)
        ol.append(userdata.detected_obj)
        rl.append(userdata.dest_room)
        userdata.objects_done = ol
        userdata.rooms_done = rl

        # Return to the room being tidied
        self._nav(userdata.target_room)

        # Person check after returning (tidying, not carrying)
        rospy.sleep(1.5)
        if self.latest == 'person':
            speak('I am tidying the {}'.format(userdata.target_room))
            self.latest = None

        return 'delivered'
