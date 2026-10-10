"""Stand-ins for the ROS packages so the state logic can be imported without ROS.

Only the names that scripts/states.py touches at import time or inside the
methods under test are provided. Nothing here talks to a robot.
"""
import os
import sys
import types

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
sys.path.insert(0, SCRIPTS)


def _module(name, **attrs):
    module = types.ModuleType(name)
    module.__dict__.update(attrs)
    sys.modules[name] = module
    return module


class _Publisher:
    def __init__(self, *args, **kwargs):
        self.published = []

    def publish(self, message):
        self.published.append(message)


class _State:
    def __init__(self, outcomes=None, input_keys=None, output_keys=None):
        self.outcomes = outcomes or []


class _Vector:
    x = y = z = 0.0


class _Twist:
    def __init__(self):
        self.linear = _Vector()
        self.angular = _Vector()


class _ActionClient:
    def __init__(self, *args, **kwargs):
        pass


_module(
    "rospy",
    Publisher=_Publisher,
    Subscriber=lambda *args, **kwargs: None,
    sleep=lambda seconds: None,
    loginfo=lambda *args, **kwargs: None,
    Duration=lambda seconds: seconds,
    Time=types.SimpleNamespace(now=lambda: 0),
)
_module("smach", State=_State)
_module("actionlib", SimpleActionClient=_ActionClient, GoalStatus=types.SimpleNamespace(SUCCEEDED=3))
_module("geometry_msgs")
_module("geometry_msgs.msg", Twist=_Twist)
_module("std_msgs")
_module("std_msgs.msg", String=str)
_module("move_base_msgs")
_module("move_base_msgs.msg", MoveBaseAction=object, MoveBaseGoal=object)
_module("tf")
_module("tf.transformations", quaternion_from_euler=lambda roll, pitch, yaw: (0.0, 0.0, 0.0, 1.0))
