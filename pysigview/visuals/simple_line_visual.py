#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 11 13:14:18 2017

Ing.,Mgr. (MSc.) Jan Cimbálník, PhD.
Biomedical engineering
International Clinical Research Center
St. Anne's University Hospital in Brno
Czech Republic
&
Mayo systems electrophysiology lab
Mayo Clinic
200 1st St SW
Rochester, MN
United States
"""

# Std imports

# Third pary imports
from vispy import gloo, visuals
from vispy.visuals.shaders import Function
import numpy as np
from vispy.scene.visuals import create_visual_node
import OpenGL.GL as GL

# Local imports

vec1to4 = Function("""
    in int gl_VertexID;
    vec4 vec1to4(float inp) {
        return vec4(gl_VertexID, inp, 0, 1);
    }
""")

vec2to4 = Function("""
    vec4 vec2to4(vec2 inp) {
        return vec4(inp, 0, 1);
    }
""")

vec3to4 = Function("""
    vec4 vec3to4(vec3 inp) {
        return vec4(inp, 1);
    }
""")


VERTEX_SHADER = """
varying vec4 v_color;

void main() {
   gl_Position = $transform($to_vec4($position));
   v_color = $color;
}
"""

FRAGMENT_SHADER = """
varying vec4 v_color;

void main() {
  gl_FragColor = v_color;
}
"""


class SimpleLineVisual(visuals.Visual):
    def __init__(self, pos=None, color=(0.5, 0.5, 0.5, 1), width=1,
                 index=None, resample=False, max_points=10000):
        visuals.Visual.__init__(self, VERTEX_SHADER, FRAGMENT_SHADER)

        self._pos = pos
        self._color = np.array(color, 'float32')
        self._width = width
        self._index = index
        self._resample = resample
        self._max_points = 10000

        self._conn = None
        self._bounds = None

        self._changed = {'pos': True, 'color': True,
                         'width': True, 'index': True}

        self.set_gl_state('translucent')

        GL.glEnable(GL.GL_LINE_SMOOTH)

        self._pos_vbo = gloo.VertexBuffer()
        self._color_vbo = gloo.VertexBuffer()
        self._index_buffer = gloo.IndexBuffer()

        self._draw_mode = 'lines'

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, pos):

        if pos is not None:
            if self._pos is not None and len(pos) != len(self._pos):
                self._index = None
                self._changed['index'] = True
        self._pos = pos
        self._changed['pos'] = True
        self.update()

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, color):
        self._color = color
        self._changed['color'] = True
        self.update()

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, width):
        self._width = width
        self._changed['width'] = True
        self.update()

    @property
    def index(self):
        return self._index

    @index.setter
    def index(self, index):
        self._index = index
        self._changed['index'] = True
        self.update()

    @property
    def max_points(self):
        return self._max_points

    @max_points.setter
    def max_points(self, max_points):
        self._max_points = max_points

    def _prepare_transforms(self, view):
        view.view_program.vert['transform'] = view.get_transform()

    def _prepare_draw(self, view):

        if self._pos is None:
            return False

        if self._width == 0:
            return False

        if self._resample:
            if self._pos.shape[-1] == 1:
                self.resample_signal(0)
            else:
                self.resample_signal(1)

        if self._changed['pos']:
            self._pos_vbo.set_data(self._pos)
            self.shared_program.vert['position'] = self._pos_vbo
            if self._pos.shape[-1] == 1:
                self.shared_program.vert['to_vec4'] = vec1to4
            elif self._pos.shape[-1] == 2:
                self.shared_program.vert['to_vec4'] = vec2to4
            elif self._pos.shape[-1] == 3:
                self.shared_program.vert['to_vec4'] = vec3to4

            # Update line connections
            self._conn = np.empty((len(self.pos), 2), dtype=np.uint32)
            self._conn[:] = np.arange(len(self.pos))[:, np.newaxis]
            self._conn[:, 1] += 1
            self._conn[-1, 1] = self._conn[-1, 0]

            # Update color if needed - this is likely inefficient
            if len(self._pos) != len(self._color):
                self._color = np.resize(self._color, (len(self._pos), 4))
                self._changed['color'] = True

            self._changed['pos'] = False

        if self._changed['color']:
            if self._color.ndim == 1:
                n = len(self.pos)
                self._color = np.tile(self._color, n).reshape(n, 4)
            self._color_vbo.set_data(self._color)
            self.shared_program.vert['color'] = self._color_vbo
            self._changed['color'] = False

        if self._changed['width']:
            px_scale = self.transforms.pixel_scale
            width = px_scale * self._width
            GL.glLineWidth(max(width, 1.))
            self._changed['width'] = False

        if self._changed['index']:
            if self._index is None:
                self._index = np.ones(len(self.pos), 'bool')

            sub_conn = self._conn[self._index]
            sub_conn[:-1, 0] = sub_conn[1:, 1]
            self._index_buffer.set_data(sub_conn)
            self._changed['index'] = False

    def _compute_bounds(self, axis, view):

        # Can and should we calculate bounds?
        if (self._bounds is None) and self._pos is not None:
            pos = self._pos
            self._bounds = [(pos[:, d].min(), pos[:, d].max())
                            for d in range(pos.shape[1])]

        # Return what we can
        if self._bounds is None:
            return
        else:
            if axis < len(self._bounds):
                return self._bounds[axis]
            else:
                return (0, 0)


SimpleLine = create_visual_node(SimpleLineVisual)
