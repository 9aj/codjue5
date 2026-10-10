import unittest
from map_pipeline.movement import validate_shapes, validate_policy
from map_pipeline.parser import MapError


class MovementContractTests(unittest.TestCase):
    def test_boxes_and_rotated_convex_are_supported(self):
        validate_shapes({'box_elems': 2, 'convex_elems': 1})

    def test_single_curved_shape_invalidates_whole_mesh(self):
        for key in ('sphere_elems', 'sphyl_elems', 'tapered_capsule_elems', 'level_set_elems'):
            with self.subTest(key=key), self.assertRaises(MapError):
                validate_shapes({'box_elems': 2, key: 1})

    def test_missing_and_triangle_collision_fail(self):
        with self.assertRaises(MapError):validate_shapes({})
        with self.assertRaises(MapError):validate_shapes({'box_elems': 1}, True)
        with self.assertRaises(MapError):validate_policy('triangles')

    def test_nonblocking_tools_and_convex_dop_are_supported(self):
        for policy in ('box', 'convex', 'dop26', 'none'):validate_policy(policy)
