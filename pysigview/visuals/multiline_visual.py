#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Oct 14 19:06:20 2018

Multiline visual

Ing.,Mgr. (MSc.) Jan Cimbálník
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

from vispy import gloo, visuals
import OpenGL.GL as GL
from vispy.scene.visuals import create_visual_node
from vispy.visuals.shaders import Function
import numpy as np

vec1to4 = Function("""
    in int gl_VertexID;
    vec4 vec1to4(float inp) {
        return vec4(gl_VertexID, inp, 0, 1);
    }
""")

vec2to4 = Function("""
    //in int gl_VertexID;
    vec4 vec2to4(vec2 inp) {
        return vec4(inp, 0, 1);
    }
""")

vec3to4 = Function("""
    //in int gl_VertexID;
    vec4 vec3to4(vec3 inp) {
        return vec4(inp, 1);
    }
""")

VERTEX_SHADER = """

uniform int n_lines;

// Atributes
attribute vec2 position;
attribute float color;

// Samplers
uniform sampler1D indices;
uniform sampler1D offsets;
uniform sampler1D scales;
uniform sampler1D lut;

// For fragment shader
varying vec4 v_color;
varying float v_discard;

void main() {

   float indices_f;
   vec4 offset_vec;
   vec4 scales_vec;

   float i;
   float temp_val;

   vec4 pos = $to_vec4(position);

   // Find the line index
   for (i = 0; i < n_lines; ++i){
           temp_val = texture1D(indices, (i+0.0001) / float(n_lines)).g;
           if (pos.x < temp_val){
                   break;
           }
   }

   // Determine if this is the last vertex of a line
   temp_val = texture1D(indices, (i+0.0001) / float(n_lines)).a;
   if (temp_val - pos.x < 0.001){
           v_discard = 1;
   }else{
           v_discard = 0;
   }

   indices_f = float(texture1D(indices, (i+0.0001) / float(n_lines)).r);
   offset_vec = vec4(texture1D(offsets, (i+0.0001) / float(n_lines)).rgb, 0);
   scales_vec = vec4(texture1D(scales, (i+0.0001) / float(n_lines)).rg, 1, 1);

   pos.x -= indices_f;
   pos *= scales_vec;
   pos += offset_vec;

   gl_Position = $transform(pos);

   // Determine the color from LUT lookup
   v_color = vec4(texture1D(lut, (color+0.0001)).rgba);
}
"""

FRAGMENT_SHADER = """
varying vec4 v_color;
varying float v_discard;

void main() {

  if (v_discard != 0.){ // this discards two segments :-(
          discard;
  }

  gl_FragColor = v_color;
}
"""


class MultilineVisual(visuals.Visual):
    def __init__(self, pos=None, columns=None, offsets=None, scales=None,
                 color=(0.5, 0.5, 0.5, 1),  width=1, index=None,
                 visibility=None):
        visuals.Visual.__init__(self, VERTEX_SHADER, FRAGMENT_SHADER)

        self._update_lock = False

        self._need_pos_update = True
        self._need_color_update = True
        self._need_indices_update = True
        self._need_index_update = True
        self._need_scales_update = True
        self._need_offsets_update = True

        # Data
        if pos is None:
            pos = np.empty(1, dtype=object)
            pos[0] = np.array([0], dtype=np.float32)
        self._line_sizes = np.array([len(x) for x in pos])
        self._pos_len = np.sum(self._line_sizes)
        if pos.dtype != 'O':
            new_pos = np.empty(pos.shape[0], dtype=object)
            for i, p in enumerate(pos):
                new_pos[i] = p
            self._pos = new_pos
        else:
            self._pos = pos

        # Visibility
        if visibility is None:
            self._visibility = np.ones(self._pos.shape[0], bool)
        else:
            self._visibility = visibility

        # Width
        self._width = width

        # Indices
        self._update_indices()

        # Index
        self._conn = np.arange(self._pos_len, dtype=np.uint32)
        if index is None:
            self._index = np.ones(self._pos_len, 'bool')
        else:
            self._index = index

        # Offsets
        if offsets is None:
            self._offsets = np.ones((self._pos.shape[0], 3), np.float32)
        else:
            self._offsets = offsets

        # Scales
        if scales is None:
            self._scales = np.ones((self._pos.shape[0], 3), np.float32)
        else:
            self._scales = scales

        self._bounds = None

        self.set_gl_state('translucent', line_width=self._width)
        GL.glEnable(GL.GL_LINE_SMOOTH)

        # Construct LUT lookup and color array

        if isinstance(color, tuple):
            self._lut = np.array(color).reshape(1, 4).astype(np.float32)
            self._color = np.zeros(self._pos_len, np.float32)
        elif isinstance(color, np.ndarray) and color.shape[0] == pos.shape[0]:
            self._lut = color
            self._color = np.zeros(self._pos_len, np.float32)
            for i, idx in enumerate(self._indices):
                self._color[int(idx[0]):int(idx[1])] = i
        else:
            self._lut = np.unique(self._color, axis=0)
            self._color = color.astype(np.float32)
            for i, c in enumerate(self._lut):
                self.color[np.where((self.color == c).all(axis=1))[0], 0] = i
            self._color = self._color[:, 0]

        # Samplers
        self._indices_tex = gloo.Texture1D(self._indices.astype(np.float32),
                                           internalformat='rgba32f')
        self.shared_program['indices'] = self._indices_tex

        self._offsets_tex = gloo.Texture1D(self._offsets.astype(np.float32),
                                           internalformat='rgb32f')
        self.shared_program['offsets'] = self._offsets_tex

        self._scales_tex = gloo.Texture1D(self._scales.astype(np.float32),
                                          internalformat='rgb32f')
        self.shared_program['scales'] = self._scales_tex

        self._lut_tex = gloo.Texture1D(self._lut.astype(np.float32),
                                       internalformat='rgba32f')
        self.shared_program['lut'] = self._lut_tex

        # Buffers
        self.shared_program.vert['to_vec4'] = vec2to4

        self._pos_vbo = gloo.VertexBuffer()
        self.shared_program['position'] = self._pos_vbo

        self._color_vbo = gloo.VertexBuffer()
        self.shared_program['color'] = self._color_vbo

        self._index_buffer = gloo.IndexBuffer()

        # Variables
        self.shared_program['n_lines'] = len(self._line_sizes)

        self._draw_mode = 'line_strip'

    # ----- Update functions -----

    def _update_indices(self):
        self._indices = np.c_[np.hstack([0, np.cumsum(self._line_sizes)[:-1]]),
                              np.cumsum(self._line_sizes),
                              np.arange(0, 1, 1/len(self._line_sizes)),
                              np.cumsum(self._line_sizes) - 1]

    def _update_index(self):

        len_diff = self._pos_len - len(self._index)
        if len_diff > 0:
            self._index = np.hstack([self._index, np.ones(len_diff,
                                                          dtype=bool)])
        elif len_diff < 0:
            self._index = self._index[:len_diff]

        self._conn = np.arange(self._pos_len, dtype=np.uint32)

    def _update_colors(self):

        len_diff = self._pos_len - len(self._color)
        if len_diff > 0:
            self._color = np.hstack([self._color,
                                     np.repeat(self._color[-1], len_diff)])
        elif len_diff < 0:
            self._color = self._color[:len_diff]

    def _update_scales(self):

        len_diff = len(self._pos) - self._scales.shape[0]
        if len_diff > 0:
            self._scales = np.vstack([self._scales,
                                      np.repeat([self._scales[-1]], len_diff,
                                                0)])
        elif len_diff < 0:
            self._scales = self._scales[:len_diff]

    def _update_offsets(self):

        len_diff = len(self._pos) - self._offsets.shape[0]
        if len_diff > 0:
            self._offsets = np.vstack([self._offsets,
                                      np.repeat([self._offsets[-1]], len_diff,
                                                0)])
        elif len_diff < 0:
            self._offsets = self._offsets[:len_diff]

    def _update_visibility(self):

        len_diff = len(self._pos) - self._visibility.shape[0]
        if len_diff > 0:
            self._visibility = np.hstack([self._visibility,
                                          np.ones(len_diff, 'bool')])
        elif len_diff < 0:
            self._visibility = self._visibility[:len_diff]

    # ----- LUT -----
    @property
    def lut(self):
        return self._lut

    @lut.setter
    def lut(self, lut):
        self._lut = lut.astype(np.float32)
        self._lut_tex.set_data(self._lut)
        if not self._update_lock:
            self.update()

    # ----- Line visibility -----
    @property
    def visibility(self):
        return self._visibility

    @visibility.setter
    def visibility(self, visibility):
        self._visibility = np.array(visibility, bool)
        self._need_index_update = True
        if not self._update_lock:
            self.update()

    def set_line_visibility(self, visibility, line_i):
        self._visibility[line_i] = visibility
        self._need_index_update = True
        if not self._update_lock:
            self.update()

    # ----- Line positions -----

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, pos):

        self._line_sizes = np.array([len(x) for x in pos])
        self._pos_len = np.sum(self._line_sizes)
        if pos.dtype != 'O':
            new_pos = np.empty(pos.shape[0], dtype=object)
            for i, p in enumerate(pos):
                new_pos[i] = p
            self._pos = new_pos
        else:
            self._pos = pos

        self._update_indices()
        self._update_colors()
        self._update_index()
        self._update_offsets()
        self._update_scales()
        self._update_visibility()

        self._need_pos_update = True
        self._need_indices_update = True
        self._need_color_update = True
        self._need_index_update = True
        self._need_scales_update = True
        self._need_offsets_update = True

        if not self._update_lock:
            self.update()

    def set_line_pos(self, pos, line_i):
        # Get the line start
        start = self._indices[line_i, 0]
        stop = self._indices[line_i, 1]

        if pos is None:
            pos = np.array([0])

        if len(pos) != stop-start:
            self._pos[line_i] = np.array(pos, np.float32)
            self._line_sizes = np.array([len(x) for x in self._pos])
            self._pos_len = np.sum(self._line_sizes)

            self._update_indices()
            self._update_colors()
            self._update_index()
            self._update_visibility()

            self._need_pos_update = True
            self._need_indices_update = True
            self._need_color_update = True
            self._need_index_update = True

        else:
            self._pos[line_i] = pos
            pos = np.c_[np.arange(len(pos), dtype=np.float32) + start,
                        pos]
            self._pos_vbo.set_subdata(pos, int(start))
        if not self._update_lock:
            self.update()

    # ----- Color -----

    def _update_lut_color(self):
        """
        Remove unused colores form lut and adjust color array.
        """

        unique_vals = np.sort(np.unique(self._color))

        lut_indices = np.arange(self._lut.shape[0])

        missing_indices = list(set(lut_indices) - set(unique_vals))
        missing_indices.sort(reverse=True)

        for mi in missing_indices:
            # Pop from lut and adjust color array
            self._lut = np.delete(self._lut, mi, 0)
            self._color[self._color > mi] -= 1

        self._lut_tex.set_data(self._lut.astype(np.float32))
        self._color_vbo.set_data(self._color / self._lut.shape[0])

    @property
    def color(self):
        if self._pos.dtype == 'O':
            color_out = np.empty(len(self._line_sizes), dtype=object)
            arr_i = 0
            for i, p in enumerate(self._pos):
                color_out[i] = self._color[arr_i:arr_i+len(p)]
                arr_i += len(p)
            return color_out
        else:
            return self._color.reshape(self._pos.shape)

    @color.setter
    def color(self, color):

        color = np.atleast_2d(color)
        color = color.astype(np.float32)

        # Add entries to lut
        for c in color:
            if not len(np.where((self._lut == c).all(axis=1))[0]):
                self._lut = np.vstack((self._lut, c)).astype(np.float32)

        if color.shape[0] == 1:
            self._color[:] = np.where((self._lut == color).all(axis=1))[0][0]
        else:
            for i, c in zip(self._indices, color):
                ci = np.where((self._lut == c).all(axis=1))[0][0]
                self._color[int(i[0]):int(i[1])] = ci

        self._update_lut_color()
        if not self._update_lock:
            self.update()

    def set_line_color(self, color, line_i, c_start=None, c_stop=None):

        color = np.atleast_2d(color)
        color = color.astype(np.float32)
        color_len = color.shape[0]

        # Add entries to lut
        for c in color:
            if not len(np.where((self._lut == c).all(axis=1))[0]):
                self._lut = np.vstack((self._lut, c)).astype(np.float32)

        # Convert entries to lists
        if not (isinstance(line_i, list) or isinstance(line_i, np.ndarray)):
            line_i = [line_i]

        if not (isinstance(c_start, list) or isinstance(c_start, np.ndarray)):
            c_start = [c_start]

        if not (isinstance(c_stop, list) or isinstance(c_stop, np.ndarray)):
            c_stop = [c_stop]

        if not(len(line_i) == len(c_start) == len(c_stop)):
            raise ValueError('Size of line index list differs from '
                             'start and stop list')

        for i in range(len(line_i)):

            start = self._indices[line_i[i], 0]
            stop = self._indices[line_i[i], 1]

            if c_start[i] is None:
                c_start[i] = start
            else:
                c_start[i] += start

            if c_stop[i] is None:
                c_stop[i] = stop
            else:
                c_stop[i] += start

            if not start <= c_start[i] < stop:
                raise ValueError('Start sample out of line range')
                return

            if not start < c_stop[i] <= stop:
                raise ValueError('Stop sample out of line range')
                return

            ci = i % color_len

            pointer = np.where((self._lut == color[ci]).all(axis=1))[0][0]
            self._color[int(c_start[i]):int(c_stop[i])] = pointer

        self._update_lut_color()
        if not self._update_lock:
            self.update()

    # ----- Array resize for scales and offsets -----

    def _array_resize(self, res_array):
        res_array = np.array(res_array, np.float32)
        if res_array.ndim < 2:
            res_array.resize(1, len(res_array))
        elif res_array.ndim > 2:
            raise RuntimeError('Array must have <= 2 dimensions')

        if res_array.shape[1] == 1:
            res_array = np.c_[res_array,
                              np.zeros(res_array.shape[0]),
                              np.zeros(res_array.shape[0])]
        elif res_array.shape[1] == 2:
            res_array = np.c_[res_array,
                              np.zeros(res_array.shape[0])]

        return res_array

    # ----- Line offsets -----

    @property
    def scales(self):
        return self._scales

    @scales.setter
    def scales(self, scales):
        scales = self._array_resize(scales)
        self._scales = scales
        self._scales_tex.set_data(self._scales.astype(np.float32))
        if not self._update_lock:
            self.update()

    def set_line_scales(self, scales, line_i):
        scales = self._array_resize(scales)
        self._scales[line_i, :] = scales
        self._scales_tex.set_data(self._scales)
        if not self._update_lock:
            self.update()

    # ----- Line offsets -----

    @property
    def offsets(self):
        return self._offsets

    @offsets.setter
    def offsets(self, offsets):
        offsets = self._array_resize(offsets)
        self._offsets = offsets
        self._offsets_tex.set_data(self._offsets.astype(np.float32))
        if not self._update_lock:
            self.update()

    def set_line_offsets(self, offsets, line_i):
        offsets = self._array_resize(offsets)
        self._offsets[line_i, :] = offsets
        self._offsets_tex.set_data(self._offsets)
        if not self._update_lock:
            self.update()

    # ----- Index buffer / line connections -----

    @property
    def index(self):
        return self._index

    @index.setter
    def index(self, index):
        self._index = index

        self._apply_visibility()
        new_conn = self._create_new_conn()

        self._index_buffer.set_data(new_conn)
        if not self._update_lock:
            self.update()

    def set_line_index(self, index, line_i):

        start = int(self._indices[line_i, 0])
        stop = int(self._indices[line_i, 1])
        self._index[start:stop] = index

        self._apply_visibility()
        new_conn = self._create_new_conn()

        self._index_buffer.set_data(new_conn)

        if not self._update_lock:
            self.update()

    def _apply_visibility(self):
        index = self._index.copy()
        for vis, idx in zip(self._visibility, self._indices):
            start = int(idx[0])
            stop = int(idx[1])
            index[start:stop] *= vis

        return index

    def _create_new_conn(self):
        new_conn = self._conn[self._apply_visibility()]

        # Adjust indices
        for i, idx in enumerate(self._indices):
            if any(new_conn[new_conn < idx[1]]):
                idx[3] = new_conn[new_conn < idx[1]][-1]
        self._indices_tex.set_data(self._indices.astype(np.float32))

        return new_conn

    def set_data(self, pos=None, color=None, index=None, scales=None,
                 offsets=None, visibility=None, line_i=None):

        # Disable visual updates in property functions
        self._update_lock = True

        if line_i is None:
            if pos is not None:
                self.pos = pos
            if color is not None:
                self.color = color
            if index is not None:
                self.index = index
            if scales is not None:
                self.scales = scales
            if offsets is not None:
                self.offsets = offsets
            if visibility is not None:
                self.visibility = visibility
        elif isinstance(line_i, int):
            if pos is not None:
                self.set_line_pos(pos, line_i)
            if color is not None:
                self.set_line_color(color, line_i)
            if index is not None:
                self.set_line_index(index, line_i)
            if scales is not None:
                self.set_line_scales(scales, line_i)
            if offsets is not None:
                self.set_line_offsets(offsets, line_i)
            if visibility is not None:
                self.set_line_visibility(visibility, line_i)
        else:
            raise ValueError('Line index must be None or int')

        self._update_lock = False
        self.update()

    def _prepare_transforms(self, view):
        view.view_program.vert['transform'] = view.get_transform()

    def _prepare_draw(self, view):
        if self._pos is None:
            return False

        if self._need_pos_update:
            pos = np.hstack(self._pos).astype(np.float32)
            pos = np.c_[np.arange(self._pos_len, dtype=np.float32), pos]
            self._pos_vbo.set_data(pos)
            self.shared_program['n_lines'] = len(self._line_sizes)
            self._need_pos_update = False

        if self._need_indices_update:
            self._indices_tex.set_data(self._indices.astype(np.float32))
            self._need_indices_update = False

        if self._need_color_update:
            self._color_vbo.set_data(self._color / self._lut.shape[0])
            self._need_color_update = False

        if self._need_index_update:
            self._index_buffer.set_data(self._create_new_conn())
            self._need_index_update = False

        if self._need_scales_update:
            self._scales_tex.set_data(self._scales.astype(np.float32))
            self._need_scales_update = False

        if self._need_offsets_update:
            self._offsets_tex.set_data(self._offsets.astype(np.float32))
            self._need_offsets_update = False


Multiline = create_visual_node(MultilineVisual)
