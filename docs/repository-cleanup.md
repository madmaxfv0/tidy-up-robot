# Repository cleanup

What changed when the coursework submission was turned into this repository.

## Source of the files

The `Tidy_up_robot` working folder and the submitted archive were identical apart from a `.DS_Store` file.

## Structure

The catkin package sits at the repository root, unchanged in layout (`action/`, `cfg/`, `launch/`, `scripts/`, `CMakeLists.txt`, `package.xml`), so it can be cloned straight into a workspace.

The package is still named `second_coursework`. Renaming it means changing `package.xml`, `CMakeLists.txt`, both launch files and the generated message imports, and that could not be tested without a ROS environment.

## Left out

| Item | Reason |
|---|---|
| `itr_cw_AI_2526` (Linux executable) | The module's video-playback node. Course material, and a compiled binary. |
| `scripts/__pycache__/` | Generated. |
| The coursework brief | Module material, not mine to redistribute. |

Nothing was deleted from the original folders.

## Code changes

One. `scripts/yolo_detector.py` located `cfg/coco.data` through an absolute path inside one user's home directory. It now asks ROS for the package path:

```python
meta_path=os.path.join(rospkg.RosPack().get_path('second_coursework'), 'cfg', 'coco.data')
```

This change is syntax-checked but has not been run under ROS.

## Added

- `tests/` — decision-logic tests with ROS stubbed out.
- `.github/workflows/ci.yml`, `.gitignore`.
- `README.md`, `docs/interfaces.md`.
