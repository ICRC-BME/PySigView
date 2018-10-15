#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 29 09:23:17 2017

General data loading buffer that will be transferred to Pysigview

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

# Standard library imports
from collections import Sequence

# Third party imports
import numpy as np
import bcolz as bc

# Local imports


class MultiRingBuffer(Sequence):
    def __init__(self, n_elements, sizes=None, dtype=float, datadir=None):
        """
        Create a new ring buffer with the given number of elements\n
        individual element size and element type

        Parameters:
        -----------
        n_elements: int
            The number of elements (individual ring buffers)
        sizes: int, list or array
            Size for all elements or list/array with sizes for elements
        dtype: data-type, optional (default=float)
            Data type of the ring buffer
        datadir: str
            If specified the data is stored on disk (default=None)
        """

        self._arr = np.empty(n_elements, object)
        if isinstance(sizes, (list, np.ndarray)):
            self._sizes = np.array(sizes)
            for i in range(len(self._arr)):
                if datadir is not None:
                    self._arr[i] = bc.zeros(int(sizes[i]), dtype,
                                            rootdir=datadir + '/arr_' + str(i),
                                            mode='w')
                else:
                    self._arr[i] = bc.zeros(int(sizes[i]), dtype)
        elif isinstance(sizes, int):
            self._sizes = np.array([sizes]*len(self._arr))
            for i in range(len(self._arr)):
                if datadir is not None:
                    self._arr[i] = bc.zeros(int(sizes), dtype,
                                            rootdir=datadir + '/arr_' + str(i),
                                            mode='w')
                else:
                    self._arr[i] = bc.zeros(int(sizes), dtype)

        self._dtype = dtype
        self._sizes = np.zeros(n_elements, int)
        if sizes is not None:
            self._sizes += sizes
        self._indices = np.zeros(n_elements, dtype=int)

    def roll(self, by, elements=None):
        """
        Roll the multiring

        Parameters:
        -----------
        by: int or array
            value by which the elements will be rolled
        elements: np.array or slice (optional)
            roll only selected elements

        Note: to roll right use negative value in by argument.
        """

        if elements is None:
            self._indices += by
        else:
            self._indices[elements] += by

#    def change_size(self, by, elements=None, fb_ratio=1):
#        """
#        Change size of elements. Enlarged section is filled with 0s.
#
#        Parameters:
#        -----------
#        by: int
#            the size of change for element(s) - (+) enlarged, (-) shrunk
#        elements: np.array or slice (optional)
#            enlarge only selected elements
#        fb_ratio: float (0-1)
#            the ratio between number of points added to front and back of\n
#            the buffer. 1=front of the buffer appended, 0=back of the\n
#            buffer is prepended
#        """
#
#        if elements is None:
#            elements = range(len(self._arr))
#        elif elements.dtype == 'bool':
#            elements = np.where(elements)[0]
#
#        if by > 0:
#
#            for e in elements:
#
#                curr_idx = self._indices[e] % self._sizes[e]
#                app_arr = np.zeros(self._sizes[e]+by, self._dtype)
#                app_arr[:curr_idx] = self._arr[e][:curr_idx]
#
#                self._sizes[e] += by
#                if self._indices[e] < 0:
#                    new_idx = self._indices[e] % self._sizes[e]
#                else:
#                    self._indices[e] += by
#                    new_idx = self._indices[e] % self._sizes[e]
#
#                app_arr[new_idx:] = self._arr[e][curr_idx:]
#                self._arr[e] = app_arr
#
#                self._indices[e] -= int(by * (1 - fb_ratio) + 0.5)
#
#        elif by < 0:
#
#            for e in elements:
#
#                start_s = int((by * (1 - fb_ratio)) - 0.5)
#                stop_s = self._sizes[e] + int(by * fb_ratio)
#
#                idx_a = self._apply_indices(e)
#                idx_a = idx_a[start_s:stop_s]
#
#                self._indices[e] = 0
#                self._sizes[e] += by
#                self._arr[e] = self._arr[e][idx_a]
#
#        else:
#            raise RuntimeError('By value has to be different than 0')

    def enlarge(self, by, elements=None, fb_ratio=1):
        """
        Enlarge elements by size. Enlarged by zeros.

        Parameters:
        -----------
        by: int
            the size by which the element(s) is enlarged
        elements: np.array or slice (optional)
            enlarge only selected elements
        fb_ratio: float (0-1)
            the ratio between number of points added to front and back of\n
            the buffer. 1=front of the buffer appended, 0=back of the\n
            buffer is prepended
        """

        if elements is None:
            elements = range(len(self._arr))
        elif elements.dtype == 'bool':
            elements = np.where(elements)[0]

        for e in elements:

            ci = self._indices[e] % self._sizes[e]
            size = self._sizes[e]

            self._arr[e].resize(size + by)
            self._arr[e][-(size-ci):] = self._arr[e][ci:size]
            self._arr[e][ci:size] = 0

            self._indices[e] = ci + by
            self._indices[e] -= int(by * (1 - fb_ratio) + 0.5)
            self._sizes[e] += by

            self._arr[e].flush()

    def shrink(self, by, elements=None, fb_ratio=0.5):
        """
        Shrink elements by size. Shrunk by 1/2 of size at the start and end.

        Parameters:
        -----------
        by: int
            the size by which the element(s) is shrunk
        elements: np.array or slice (optional)
            shrink only selected elements
        fb_ratio: float (0-1)
            the ratio between number of points taken from front and back of\n
            the buffer. 1=front of the buffer is cut off, 0=back of the\n
            buffer is cut off
        """

        if elements is None:
            elements = range(len(self._arr))
        elif elements.dtype == 'bool':
            elements = np.where(elements)[0]

        for e in elements:

            self._indices[e] += int(by * fb_ratio)
            idx_a = self._apply_indices(e)

            self._indices[e] = 0
            self._sizes[e] -= by

            if isinstance(idx_a, slice) and idx_a.start < 0:
                temp_arr = self._arr[e][idx_a.start:]
                self._arr[e][-idx_a.start:] = self._arr[e][:idx_a.stop]
                self._arr[e][:-idx_a.start] = temp_arr
            else:
                self._arr[e][idx_a] = self._arr[e][idx_a]

            self._arr[e].resize(self._sizes[e])

            self._arr[e].flush()

    def purge_data(self):

        for a in self._arr:
            a.purge()

    def _apply_indices(self, e, s=None):

        el = self._sizes[e]

        # Apply indices
        if s is None:
            s = slice(-self._sizes[e] + (self._indices[e] % self._sizes[e]),
                      self._indices[e] % self._sizes[e], 1)
        elif isinstance(s, int):
            s = (self._indices[e] + s) % el
        elif isinstance(s, slice):
            if s.start is None:
                new_start = self._indices[e]
            else:
                new_start = (s.start + self._indices[e]) % self._sizes[e]
            if s.stop is None:
                new_stop = self._sizes[e] + self._indices[e]
            else:
                new_stop = (s.stop + self._indices[e]) % self._sizes[e]
            if new_stop < new_start:
                new_start = -self._sizes[e] + new_start
            s = slice(new_start, new_stop, s.step)
        else:
            s = (s + self._indices[e]) % self._sizes[e]

        return s

    def _set_element(self, e, val, s=None):

        if s is not None:
            s = self._apply_indices(e, s)
            if isinstance(s, slice) and s.start < 0:
                self._arr[e][s.start:] = val[:-s.start]
                self._arr[e][:s.stop] = val[-s.start:]
            else:
                self._arr[e][s] = val
        else:
            if not isinstance(val, np.ndarray):
                raise ValueError('Only arrays can be set as elements')
            self._arr[e] = val

        self._arr[e].flush()

    def _get_element(self, e, s=None):

        if s is not None:
            s = self._apply_indices(e, s)
            if isinstance(s, slice) and s.start < 0:
                return np.hstack([self._arr[e][s.start:],
                                  self._arr[e][:s.stop]])
            else:
                return self._arr[e][s]
        else:
            s = self._apply_indices(e)
            return self._arr[e][s]

    def __repr__(self):
        return self._arr.__repr__()

    def __str__(self):
        return self._arr.__str__()

    def __len__(self):
        return len(self._arr)

    def __getitem__(self, s):

        if isinstance(s, int):
            return self._get_element(s)

        elif isinstance(s, slice):
            if s.step is None:
                r = range(s.start, s.stop)
            else:
                r = range(s.start, s.stop, s.step)
            arr_out = np.empty(len(r), object)
            for i, ai in enumerate(r):
                arr_out[i] = self._get_element(ai)
            return self._arr[s]

        elif isinstance(s, np.ndarray):
            if s.dtype == 'bool':
                arr_out = np.empty(sum(s), object)
                for i, ai in enumerate(np.where(s)[0]):
                    arr_out[i] = self._get_element(ai)
                return arr_out
            else:
                arr_out = np.empty(len(s), object)
                for i in range(len(s)):
                    arr_out[i] = self._get_element(s[i])
                return arr_out

        elif isinstance(s, tuple):

            # One element
            if isinstance(s[0], int):
                return self._get_element(s[0], s[1])

            # Fork for s1 - list, array, slice, int
            if isinstance(s[1], slice) or isinstance(s[1], int):

                if isinstance(s[0], slice):
                    if s[0].step is None:
                        r = range(s[0].start, s[0].stop)
                    else:
                        r = range(s[0].start, s[0].stop, s[0].step)
                    arr_out = np.empty(len(r), object)
                    for i, ai in enumerate(r):
                        arr_out[i] = self._get_element(ai, s[1])
                    return arr_out

                # Array or list over elements
                elif isinstance(s[0], list) or isinstance(s[0], np.ndarray):
                    arr_out = np.empty(len(s[0]), object)
                    for i in range(len(s[0])):
                        arr_out[i] = self._get_element(s[0][i], s[1])
                    return arr_out

            elif isinstance(s[1], np.ndarray):

                # Slice over elements
                if isinstance(s[0], slice):
                    if s[0].step is None:
                        r = range(s[0].start, s[0].stop)
                    else:
                        r = range(s[0].start, s[0].stop, s[0].step)
                    arr_out = np.empty(len(r), object)
                    for i, ai in enumerate(r):
                        arr_out[i] = self._get_element(ai, s[1][i])
                    return arr_out

                # Array or over elements
                elif isinstance(s[0], np.ndarray):
                    arr_out = np.empty(len(s[0]), object)
                    for i in range(len(s[0])):
                        arr_out[i] = self._get_element(s[0][i], s[1][i])
                    return arr_out
            else:
                raise ValueError('Incorrect type "'+type(s).__name__+'" only'
                                 ' integers, slices and arrays allowed')
        else:
            raise ValueError('Incorrect type "'+type(s).__name__+'" only'
                             ' integers, slices and arrays allowed')

    def __setitem__(self, s, val):

        # Assign one array to one element
        if isinstance(s, int):
            self._arr[s] = val
            return

        if isinstance(s, slice):
            if s.step is None:
                s = np.array(range(s.start, s.stop))
            else:
                s = np.array(range(s.start, s.stop, s.step))
            for e in s:
                self._set_element(e, val)

        # Assign array(s) to multiple elements
        if isinstance(s, (list, np.ndarray)):

            if np.ndim(val) == 1:
                for ai in s:
                    self._set_element(ai, val)
            elif np.ndim(val) == 2:
                for i, ai in enumerate(s):
                    self._set_element(ai, val[i])
            else:
                raise ValueError('Inserted value can have 1 or 2 dims')

        # Assign array(s) to slices over element(s)
        elif isinstance(s, tuple):
            if isinstance(s[0], int):
                self._set_element(s[0], val, s[1])
                return
            elif isinstance(s[0], slice):
                for i, ai in enumerate(range(s[0].start, s[0].stop)):
                    if isinstance(s[1], int) or np.ndim(val) == 2:
                        self._set_element(ai, val[i], s[1])
                    elif np.ndim(val) == 1:
                        self._set_element(ai, val, s[1])
                    else:
                        raise ValueError('Inserted value can have 1 or 2 dims')
            elif isinstance(s[0], np.ndarray):
                if np.ndim(val) > 2:
                    raise ValueError('Inserted value can have 1 or 2 dims')
                if np.ndim(s[1]) > 2:
                    raise ValueError('Index array can have 1 or 2 dims')

                for i, ai in enumerate(s[0]):

                    iso = isinstance(val, np.ndarray) and val.dtype == object
                    if iso or np.ndim(val) == 2:
                        vali = val[i]
                    else:
                        vali = val

                    iso = isinstance(s[1], np.ndarray) and s[1].dtype == object
                    if iso or np.ndim(s[1]) == 2:
                        si = s[1][i]
                    else:
                        si = s[1]

                    self._set_element(ai, vali, si)
        else:
            raise ValueError('Incorrect type "'+type(s).__name__+'" only'
                             ' integers, slices and arrays allowed')
