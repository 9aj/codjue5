"""Strict line-aware reader for COD/Radiant plane brushes and IW mesh grids."""
import math
import re
from dataclasses import dataclass, field

NUMBER = r'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?'
FACE = re.compile(r'^\s*\(([^()]*)\)\s*\(([^()]*)\)\s*\(([^()]*)\)\s+(\S+)\s*(.*)$')
PROPERTY = re.compile(r'^"((?:[^"\\]|\\.)*)"\s+"((?:[^"\\]|\\.)*)"\s*$')


class MapError(ValueError):
    pass


@dataclass
class Block:
    line: int
    lines: list = field(default_factory=list)
    children: list = field(default_factory=list)


def strip_comment(line):
    quoted = escaped = False
    for i, ch in enumerate(line):
        if ch == '"' and not escaped:
            quoted = not quoted
        if not quoted and line[i:i+2] == '//':
            return line[:i].strip()
        escaped = ch == '\\' and not escaped
    return line.strip()


def numbers(text, count=None):
    try:
        values = [float(x) for x in text.split()]
    except ValueError as exc:
        raise MapError('Invalid numeric data: '+text) from exc
    if (count is not None and len(values) != count) or not all(math.isfinite(x) for x in values):
        raise MapError('Invalid numeric arity or non-finite data: '+text)
    return values


def unquote(value):
    # Preserve literal Windows paths; only escaped quotes/backslashes are decoded.
    return value.replace(r'\"', '"').replace('\\\\', '\\')


def properties(block):
    return {unquote(m[1]): unquote(m[2]) for _, line in block.lines if (m := PROPERTY.fullmatch(line))}


def parse(text):
    root = Block(0)
    stack = [root]
    for number, raw in enumerate(text.splitlines(), 1):
        line = strip_comment(raw)
        if not line:
            continue
        if line == '{':
            block = Block(number)
            stack[-1].children.append(block)
            stack.append(block)
        elif line == '}':
            if len(stack) == 1:
                raise MapError(f'Unexpected closing brace at line {number}')
            stack.pop()
        else:
            if '{' in line or '}' in line:
                # Entity values can legitimately contain braces.
                if not PROPERTY.fullmatch(line):
                    raise MapError(f'Braces must occupy their own line at {number}')
            stack[-1].lines.append((number, line))
    if len(stack) != 1:
        raise MapError(f'Unclosed block beginning at line {stack[-1].line}')
    if not root.children:
        raise MapError('Map contains no entities')
    entities = []
    objects = []
    unsupported = []
    counts = {'brush': 0, 'patch': 0}
    for entity_index, entity in enumerate(root.children):
        props = properties(entity)
        entities.append({'id': f'Entity_{entity_index:05d}', 'line': entity.line, 'properties': props})
        for child in entity.children:
            header = [line for _, line in child.lines]
            candidate = child
            kind = 'brush'
            if any(x in ('mesh', 'patchDef2', 'patchDef3') for x in header):
                kind = 'patch'
                if len(child.children) != 1:
                    raise MapError(f'Patch wrapper at line {child.line} needs one grid')
                candidate = child.children[0]
            elif child.children:
                unsupported.append({'entity_id': entities[-1]['id'], 'line': child.line, 'reason': 'Unknown nested geometry', 'header': header})
                continue
            sides = []
            for line_no, line in candidate.lines:
                match = FACE.fullmatch(line)
                if match:
                    sides.append({'points': [numbers(match[i], 3) for i in (1, 2, 3)], 'material': match[4].strip('"'), 'texdef': match[5], 'line': line_no})
            if kind == 'brush' and not sides:
                unsupported.append({'entity_id': entities[-1]['id'], 'line': child.line, 'reason': 'Unknown geometry block', 'header': header})
                continue
            index = counts[kind]
            counts[kind] += 1
            objects.append({'id': f'{kind.title()}_{index:05d}', 'kind': kind, 'index': index, 'line': child.line, 'entity_id': entities[-1]['id'], 'entity': props, 'lines': candidate.lines, 'sides': sides, 'format': next((x for x in header if x in ('mesh','patchDef2','patchDef3')), 'brush')})
    return entities, objects, unsupported


def mesh_grid(obj):
    lines = [line for _, line in obj['lines']]
    if obj['format'] in ('patchDef2','patchDef3'):
        dim_index=next((i for i,line in enumerate(lines) if re.fullmatch(r'\(\s*(?:'+NUMBER+r'\s+){4,6}'+NUMBER+r'\s*\)',line)),None)
        if dim_index is None:raise MapError('Missing patchDef control-grid dimensions')
        dimensions=numbers(lines[dim_index].strip('() '));width,height=map(int,dimensions[:2])
        if dimensions[0]!=width or dimensions[1]!=height or not 3<=width<=129 or not 3<=height<=129:raise MapError('Invalid patchDef dimensions')
        material=next((line.strip('"') for line in lines[:dim_index] if re.fullmatch(r'"?[\w./-]+"?',line)),None)
        if not material:raise MapError('Missing patchDef material')
        values=[float(x) for x in re.findall(NUMBER,' '.join(lines[dim_index+1:]))]
        if not all(math.isfinite(x) for x in values) or len(values)!=width*height*5:raise MapError('Invalid patchDef point count')
        return width,height,[values[i:i+3] for i in range(0,len(values),5)],[values[i+3:i+5] for i in range(0,len(values),5)],material
    if obj['format'] != 'mesh':raise MapError('Unsupported patch format')
    dim_index = next((i for i,line in enumerate(lines) if re.fullmatch(r'\d+\s+\d+\s+\d+\s+\d+',line)), None)
    if dim_index is None:
        raise MapError('Missing IW mesh dimensions')
    width, height, _, _ = map(int, lines[dim_index].split())
    if not 2 <= width <= 129 or not 2 <= height <= 129:
        raise MapError(f'Invalid/oversized control grid {width}x{height}')
    material_lines = [s for s in lines[:dim_index] if re.fullmatch(r'[\w./-]+', s)]
    if len(material_lines) < 2:
        raise MapError('Mesh diffuse/lightmap material names are missing')
    vertices, uvs = [], []
    for line in lines[dim_index+1:]:
        if not line.startswith('v '):
            continue
        match = re.fullmatch(r'v\s+('+NUMBER+r')\s+('+NUMBER+r')\s+('+NUMBER+r')\s+t\s+(.+)', line)
        if not match:
            raise MapError('Unrecognised mesh vertex: '+line)
        vertices.append(numbers(' '.join(match[i] for i in (1,2,3)),3))
        values = numbers(match[4])
        if len(values) != 3:
            raise MapError('IW vertex texture data must have three values')
        uvs.append(values[-2:])
    if len(vertices) != width*height:
        raise MapError(f'Mesh has {len(vertices)} vertices, expected {width*height}')
    return width, height, vertices, uvs, material_lines[0]
