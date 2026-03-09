"""
VirtuCameraBlender smoke test - Blender 5.0+

Run headlessly:
    blender --background --python test_smoke.py

Run against a specific .blend file:
    blender myfile.blend --background --python test_smoke.py

Dynamic reload during development (run in Blender's Python console or Text Editor):
    # One-liner reload — paste into Blender's Python Console:
    import sys, bpy
    [sys.modules.pop(k) for k in list(sys.modules) if 'virtucamera' in k]
    bpy.ops.preferences.addon_disable(module="virtucamera_blender")
    bpy.ops.preferences.addon_enable(module="virtucamera_blender")

    # Or save the snippet below as a .py file, open it in Blender's Text Editor,
    # and hit Run Script (Alt+P) after every code change:
    #
    #   import sys, bpy
    #   [sys.modules.pop(k) for k in list(sys.modules) if 'virtucamera' in k]
    #   bpy.ops.preferences.addon_disable(module="virtucamera_blender")
    #   bpy.ops.preferences.addon_enable(module="virtucamera_blender")
    #   print("Reloaded OK")
"""

import os
import sys

# Allow Blender to find the addon when the script is run directly from the
# repo root (blender --background --python test_smoke.py).
_repo_dir = os.path.dirname(os.path.abspath(__file__))
if _repo_dir not in sys.path:
    sys.path.insert(0, _repo_dir)

import bpy

ADDON_MODULE = "virtucamera_blender"
_failures = []


def test(name, condition):
    if condition:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}")
        _failures.append(name)


def section(title):
    print(f"\n--- {title}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _enable_addon():
    bpy.ops.preferences.addon_enable(module=ADDON_MODULE)


def _disable_addon():
    bpy.ops.preferences.addon_enable(module=ADDON_MODULE)
    bpy.ops.preferences.addon_disable(module=ADDON_MODULE)


def _addon_enabled():
    return ADDON_MODULE in bpy.context.preferences.addons


def _make_camera(name="TestCam"):
    bpy.ops.object.camera_add()
    cam = bpy.context.scene.objects[-1]
    cam.name = name
    return cam


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_registration():
    section("Registration")
    _enable_addon()
    test("addon enabled", _addon_enabled())
    test("VirtuCameraState registered", hasattr(bpy.types, "VirtuCameraState"))
    test("VIEW3D_OT_virtucamera_start registered", hasattr(bpy.types, "VIEW3D_OT_virtucamera_start"))
    test("VIEW3D_OT_virtucamera_stop registered", hasattr(bpy.types, "VIEW3D_OT_virtucamera_stop"))
    test("VIEW3D_OT_virtucamera_redraw registered", hasattr(bpy.types, "VIEW3D_OT_virtucamera_redraw"))
    test("GRAPH_OT_virtucamera_euler_filter registered", hasattr(bpy.types, "GRAPH_OT_virtucamera_euler_filter"))
    test("VIEW3D_PT_virtucamera_main registered", hasattr(bpy.types, "VIEW3D_PT_virtucamera_main"))


def test_scene_property():
    section("Scene property")
    scene = bpy.context.scene
    test("scene.virtucamera exists", hasattr(scene, "virtucamera"))
    vc = scene.virtucamera
    test("tcp_port property exists", hasattr(vc, "tcp_port"))
    test("tcp_port default is 23354", vc.tcp_port == 23354)
    test("custom_scripts_dir property exists", hasattr(vc, "custom_scripts_dir"))
    test("server object exists", hasattr(vc, "server"))
    test("contexts dict exists", hasattr(vc, "contexts"))


def test_camera_queries():
    section("Camera queries")
    from virtucamera_blender.virtucamera_blender import VirtuCameraBlender
    vcb = VirtuCameraBlender()

    cam = _make_camera("SmokeTestCam")

    cameras = vcb.get_scene_cameras(None)
    test("get_scene_cameras returns list", isinstance(cameras, list))
    test("get_scene_cameras includes new camera", cam.name in cameras)

    test("get_camera_exists returns True", vcb.get_camera_exists(None, cam.name))
    test("get_camera_exists returns False for bogus", not vcb.get_camera_exists(None, "NONEXISTENT_XYZ"))

    has_keys = vcb.get_camera_has_keys(None, cam.name)
    test("get_camera_has_keys returns 2-tuple", len(has_keys) == 2)
    test("no transform keys on new camera", not has_keys[0])
    test("no focal length keys on new camera", not has_keys[1])

    flen = vcb.get_camera_focal_length(None, cam.name)
    test("get_camera_focal_length returns float", isinstance(flen, float))
    test("focal length is positive", flen > 0)


def test_camera_transform():
    section("Camera transform")
    from virtucamera_blender.virtucamera_blender import VirtuCameraBlender
    vcb = VirtuCameraBlender()

    cam = _make_camera("TransformTestCam")

    mat = vcb.get_camera_transform(None, cam.name)
    test("get_camera_transform returns 16 values", len(mat) == 16)
    test("all values are numeric", all(isinstance(v, float) for v in mat))

    # Round-trip: set then get should not crash
    vcb.set_camera_transform(None, cam.name, mat)
    test("set_camera_transform does not raise", True)

    vcb.set_camera_focal_length(None, cam.name, 50.0)
    test("set_camera_focal_length to 50mm", vcb.get_camera_focal_length(None, cam.name) == 50.0)


def test_keyframe_ops():
    section("Keyframe operations")
    from virtucamera_blender.virtucamera_blender import VirtuCameraBlender
    vcb = VirtuCameraBlender()

    cam = _make_camera("KeyTestCam")
    mat = vcb.get_camera_transform(None, cam.name)

    vcb.set_camera_transform_keys(None, cam.name, (1.0, 10.0), (mat, mat))
    has_keys = vcb.get_camera_has_keys(None, cam.name)
    test("transform keys exist after set_camera_transform_keys", has_keys[0])

    vcb.set_camera_flen_keys(None, cam.name, (1.0, 10.0), (35.0, 50.0))
    has_keys = vcb.get_camera_has_keys(None, cam.name)
    test("focal length keys exist after set_camera_flen_keys", has_keys[1])

    vcb.remove_camera_keys(None, cam.name)
    has_keys = vcb.get_camera_has_keys(None, cam.name)
    test("no transform keys after remove_camera_keys", not has_keys[0])
    test("no focal length keys after remove_camera_keys", not has_keys[1])


def test_unregistration():
    section("Unregistration")
    bpy.ops.preferences.addon_disable(module=ADDON_MODULE)
    test("addon disabled cleanly", not _addon_enabled())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("\n=== VirtuCameraBlender Smoke Tests ===")

    test_registration()
    test_scene_property()
    test_camera_queries()
    test_camera_transform()
    test_keyframe_ops()
    test_unregistration()

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} test(s) failed:")
        for f in _failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print(f"All tests passed.")


main()
