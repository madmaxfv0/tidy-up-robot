"""Checks for the tidy-up decision logic in scripts/states.py (no ROS needed)."""
import types

import pytest

import states

ROOMS = ["kitchen", "garage", "bedroom-1", "bedroom-2", "living-room", "bathroom"]


def userdata(room, done=()):
    return types.SimpleNamespace(
        target_room=room, objects_done=list(done), rooms_done=list(done),
        detected_obj="", dest_room="")


def search(room, detection, done=()):
    state = states.SearchRoom()
    state.latest = detection
    data = userdata(room, done)
    return state.execute(data), data


def test_every_room_has_a_map_position_and_an_object_list():
    assert sorted(states.ROOM_COORDS) == sorted(ROOMS)
    assert sorted(states.ROOM_OBJECTS) == sorted(ROOMS)


@pytest.mark.parametrize("obj, current, expected", [
    ("laptop", "kitchen", "bedroom-1"),
    ("toothbrush", "living-room", "bathroom"),
    ("bicycle", "bedroom-2", "garage"),
    ("book", "garage", "living-room"),
])
def test_misplaced_object_is_sent_to_a_room_where_it_belongs(obj, current, expected):
    assert states.find_destination(obj, current) == expected


def test_destination_is_never_the_room_being_tidied():
    for room in ROOMS:
        for objects in states.ROOM_OBJECTS.values():
            for obj in objects:
                assert states.find_destination(obj, room) != room


def test_object_with_no_home_has_no_destination():
    assert states.find_destination("dog", "kitchen") is None


def test_search_reports_a_misplaced_object_and_its_destination():
    outcome, data = search("kitchen", "laptop")
    assert outcome == "found_object"
    assert (data.detected_obj, data.dest_room) == ("laptop", "bedroom-1")


def test_search_ignores_an_object_that_belongs_in_the_room():
    outcome, _ = search("kitchen", "bottle")
    assert outcome == "keep_searching"


def test_search_ignores_an_object_that_belongs_nowhere():
    outcome, _ = search("kitchen", "dog")
    assert outcome == "keep_searching"


def test_search_keeps_going_when_nothing_was_detected():
    outcome, _ = search("garage", None)
    assert outcome == "keep_searching"


def test_search_reports_a_person():
    outcome, _ = search("bathroom", "person")
    assert outcome == "person_seen"


def test_search_stops_after_two_deliveries():
    outcome, _ = search("kitchen", "laptop", done=("laptop", "book"))
    assert outcome == "tidying_done"


def test_search_moves_then_stops_before_reading_detections():
    state = states.SearchRoom()
    state.execute(userdata("kitchen"))
    assert len(state.vel_pub.published) == 2
    final = state.vel_pub.published[-1]
    assert (final.linear.x, final.angular.z) == (0.0, 0.0)
    assert state.search_step == 1
