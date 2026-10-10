"""Project Jump's box/convex movement contract, shared by export and verification."""
from .parser import MapError

SHAPE_FIELDS = ('box_elems', 'convex_elems', 'sphere_elems', 'sphyl_elems',
                'tapered_capsule_elems', 'level_set_elems', 'ml_level_set_elems',
                'skinned_level_set_elems', 'skinned_triangle_mesh_elems')


def validate_policy(policy):
    if policy not in ('box', 'convex', 'dop26', 'none'):
        raise MapError('Project Jump requires box/convex movement collision: '+str(policy))


def validate_shapes(counts, complex_as_simple=False):
    """A mixed sphere/capsule invalidates the entire movement mesh, not just that shape."""
    if complex_as_simple:
        raise MapError('Movement mesh uses complex-as-simple collision')
    forbidden = {k: v for k, v in counts.items() if k not in ('box_elems', 'convex_elems') and v}
    if forbidden:
        raise MapError('Unsupported movement collision shapes: '+str(forbidden))
    if not counts.get('box_elems', 0) + counts.get('convex_elems', 0):
        raise MapError('Movement mesh has no box or convex collision')


def inspect_mesh(mesh, unreal):
    body = mesh.get_editor_property('body_setup')
    if not body:
        raise MapError('Mesh has no BodySetup: '+mesh.get_path_name())
    geometry = body.get_editor_property('agg_geom')
    counts = {key: len(geometry.get_editor_property(key)) for key in SHAPE_FIELDS}
    validate_shapes(counts, body.get_editor_property('collision_trace_flag') ==
                    unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    return counts


def inspect_level(actors, unreal):
    """Include hand-authored blocking meshes: missing shapes produce no CmWorld skip."""
    results=[]
    for actor in actors:
        for component in actor.get_components_by_class(unreal.StaticMeshComponent):
            if not component.static_mesh or component.get_collision_enabled()==unreal.CollisionEnabled.NO_COLLISION:
                continue
            if component.get_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN)!=unreal.CollisionResponseType.ECR_BLOCK:
                continue
            try:
                counts=inspect_mesh(component.static_mesh,unreal)
            except MapError as exc:
                raise MapError(actor.get_actor_label()+': '+str(exc)) from exc
            results.append(dict(actor=actor.get_actor_label(),mesh=component.static_mesh.get_path_name(),shapes=counts))
    return results
