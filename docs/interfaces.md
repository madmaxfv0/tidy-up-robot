# Interfaces

Read from the source in `scripts/`, `action/` and `launch/`.

## Nodes started by `student_nodes.launch`

| Node | Script | Purpose |
|---|---|---|
| `yolo_detector` | `scripts/yolo_detector.py` | Runs YOLOv4 on camera frames, publishes class names. |
| `tidy_server` | `scripts/tidy_server.py` | Hosts the `/tidy_room` action and the state machine. |

`scripts/states.py` is imported by `tidy_server.py`; it is not a node.

## Topics

| Topic | Type | Direction | Notes |
|---|---|---|---|
| `/camera/image` | `sensor_msgs/Image` | `yolo_detector` subscribes | Every 10th frame is kept, converted to RGB. |
| `/yolo_detections` | `std_msgs/String` | `yolo_detector` publishes; `tidy_server` and `yolo_nav` subscribe | One message per detection with confidence above 0.5. The payload is the class name. |
| `/cmd_vel` | `geometry_msgs/Twist` | `tidy_server` and `vacuum_sm` publish | Search motion. |
| `/vacuum_event` | `std_msgs/String` | `vacuum_sm` subscribes | `dirty`, `obstacle` or `battery_low`. |

## Actions

### `/tidy_room` — `second_coursework/TidyUp` (server: `tidy_server`)

```
# Goal
string room            # kitchen | garage | bedroom-1 | bedroom-2 | living-room | bathroom
---
# Result
string[] objects       # objects moved, in order
string[] rooms         # the room each was taken to
---
# Feedback
string object          # misplaced object just found
string room            # where it is being taken
```

The server succeeds when two objects have been delivered and aborts if the first navigation fails.

### `move_base` — `move_base_msgs/MoveBase` (client)

Goals are built in the `map` frame at a room's position with zero yaw. `NavigateToRoom` and `DeliverAndReturn` wait up to 15 s for the server and up to 120 s for a result.

## State machine userdata

| Key | Set by | Read by |
|---|---|---|
| `target_room`, `nav_target` | goal callback | `NAV_TO_ROOM`, `ANNOUNCE`, `SEARCH`, `SPEAK_TIDY`, `DELIVER` |
| `detected_obj`, `dest_room` | `SEARCH` | `FEEDBACK`, `DELIVER` |
| `objects_done`, `rooms_done` | `DELIVER` | `SEARCH` (stop condition), action result |

## Rooms

| Room | Map position (x, y) | Objects that belong |
|---|---|---|
| `kitchen` | 2.5, 8.5 | microwave, refrigerator, bottle, sink, fork, banana, sandwich, chair |
| `garage` | 6.5, 8.5 | bicycle, car, sports ball, skateboard, motorbike |
| `bedroom-1` | 10.5, 8.5 | bottle, laptop, suitcase, tvmonitor, sports ball, skateboard, chair, bed |
| `bedroom-2` | 2.5, 3.0 | bottle, laptop, handbag, tvmonitor, sports ball, skateboard, chair, bed |
| `living-room` | 6.5, 3.0 | tvmonitor, remote, book, clock, chair |
| `bathroom` | 10.5, 3.0 | toothbrush, toilet, sink |

Object names are the COCO class names as Darknet reports them (`tvmonitor`, `motorbike`).

## Search motion

`SEARCH` cycles through four `(linear m/s, angular rad/s)` commands, one per pass: `(0.15, 0.4)`, `(0.2, -0.3)`, `(0.18, 0.0)`, `(0.1, 0.5)`. Each is held for 2 s, then the robot stops for 1.5 s before the latest detection is read.

## Speech

| When | Sentence |
|---|---|
| First arrival | "I have arrived at the *room*" |
| Person seen while searching, or after returning | "I am tidying the *room*" |
| Person seen on arriving with an object | "I am taking the *object* to *room*" |

## The two standalone nodes

- `vacuum_sm.py`: `RANDOM_MOVE` → `CLEAN` / `AVOID` / `GO_CHARGE`, driven by messages on `/vacuum_event`; charging navigates to (6.5, 5.28) through `move_base`.
- `yolo_nav.py`: on `book`, `cell phone` or `bottle` navigates to a fixed position for each; shuts down on `apple`.
