#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 29 09:23:17 2017

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

# Third party import
import numpy as np

# Local imports
from pysigview.core.multiringbuffer import MultiRingBuffer


class PysigviewMultiRingBuffer():

    def __init__(self, n_elements, sizes=None, dtype=float,
                 uutc_ss=None, fs=None, datadir=None):

        self._mrb = MultiRingBuffer(n_elements, sizes, dtype, datadir)

        if isinstance(fs, (int, float)):
            self._fs = np.zeros(n_elements, float) + fs
        elif isinstance(fs, (list, np.ndarray)):
            self._fs = fs

        if uutc_ss is not None:
            uutc_ss = np.array(uutc_ss)
            if len(uutc_ss.shape) == 1:
                self._uutc_ss = np.zeros([n_elements, 2], int)
                self._uutc_ss[:, :] = uutc_ss
            elif len(uutc_ss.shape) == 2:
                self._uutc_ss = uutc_ss

    @property
    def uutc_ss(self):
        return self._uutc_ss

    def roll(self, by, elements=None):

        # Convert time to samples and roll
        if elements is None:
            el_iter = range(len(self._mrb))
        else:
            el_iter = iter(elements)

        for i in el_iter:
            eby = int(self._fs[i] * by / 1e6)
            self._mrb.roll(eby, np.array([i]))

        # Roll times
        if elements is None:
            self._uutc_ss += int(by)
        else:
            self._uutc_ss[elements] += int(by)

#    def change_size(self, by, elements = None, fb_ratio = 1):
#
#        # Convert time to samples and roll
#        if elements is None:
#            el_iter = range(len(self._mrb))
#        else:
#            el_iter = iter(elements)
#
#        for i in el_iter:
#            eby = int(self._fs[i] * by / 1e6)
#            if eby < 0:
#                print('\tMRB shrinking')
#                self._mrb.shrink(-eby, np.array([i]))
#            else:
#                self._mrb.enlarge(eby, np.array([i]))
#
#        # Change times
#        if elements is None:
#            self._uutc_ss[:,0] += int((by * (1-fb_ratio)) + 0.5)
#            self._uutc_ss[:,1] -= int((by * fb_ratio) + 0.5)
#        else:
#            self._uutc_ss[elements,0] += int((by * (1-fb_ratio)) + 0.5)
#            self._uutc_ss[elements,1] -= int((by * fb_ratio) + 0.5)

    def enlarge(self, by, elements=None, fb_ratio=1):

        # Convert time to samples and roll
        if elements is None:
            el_iter = range(len(self._mrb))
        else:
            el_iter = iter(elements)

        for i in el_iter:
            eby = int(self._fs[i] * by / 1e6)
            self._mrb.enlarge(eby, np.array([i]), fb_ratio)

        # Enlarge times
        if elements is None:
            self._uutc_ss[:, 0] -= int((by * (1-fb_ratio)) + 0.5)
            self._uutc_ss[:, 1] += int((by * fb_ratio) + 0.5)
        else:
            self._uutc_ss[elements, 0] -= int((by * (1-fb_ratio)) + 0.5)
            self._uutc_ss[elements, 1] += int((by * fb_ratio) + 0.5)

    def shrink(self, by, elements=None, fb_ratio=0.5):

        # Convert time to samples and roll
        if elements is None:
            el_iter = range(len(self._mrb))
        else:
            el_iter = iter(elements)

        for i in el_iter:
            eby = int(self._fs[i] * by / 1e6)
            self._mrb.shrink(eby, np.array([i]), fb_ratio)

        # Shrink times
        if elements is None:
            self._uutc_ss[:, 0] += int((by * (1-fb_ratio)) + 0.5)
            self._uutc_ss[:, 1] -= int((by * fb_ratio) + 0.5)
        else:
            self._uutc_ss[elements, 0] += int((by * (1-fb_ratio)) + 0.5)
            self._uutc_ss[elements, 1] -= int((by * fb_ratio) + 0.5)

    def purge_data(self):
        self._mrb.purge_data()

    def _create_full_slice(self, s, e):
        if s.start is None:
            start = self._uutc_ss[e][0]
        else:
            start = s.start

        if s.stop is None:
            stop = self._uutc_ss[e][1]
        else:
            stop = s.stop

        if s.step is None:
            step = (1/self._fs[e]) * 1e6
        else:
            step = s.step

        return slice(start, stop, step)

    def _check_time(self, e, t):
        if t < self._uutc_ss[e][0]:
            raise ValueError("Time {} is earlier than buffer {}".format(t,
                             self._uutc_ss[e][0]))
        if t > self._uutc_ss[e][1]:
            raise ValueError("Time {} is later than buffer {}".format(t,
                             self._uutc_ss[e][1]))

    def _uutc_to_samp(self, s):

        elements = s[0]
        t_ss = s[1]

        if isinstance(elements, int):
            elements = np.array([elements])
        elif isinstance(elements, slice):
            if elements.start is None:
                start = 0
            else:
                start = elements.start
            if elements.stop is None:
                stop = len(self._mrb)
            else:
                stop = elements.stop
            if elements.step is None:
                elements = np.arange(start, stop, dtype=int)
            else:
                elements = np.arange(start, stop, elements.step, dtype=int)

        if isinstance(t_ss, int):
            samps = np.zeros(len(elements), int)
            for i, e in enumerate(elements):
                self._check_time(e, t_ss)
                samps[i] = ((t_ss - self._uutc_ss[e][0]) / 1e6) * self._fs[e]
        elif isinstance(t_ss, slice):
            samps = np.zeros(len(elements), object)
            for i, e in enumerate(elements):
                full_t_ss = self._create_full_slice(t_ss, e)
                self._check_time(e, t_ss.start)
                self._check_time(e, t_ss.stop)
                start = (((full_t_ss.start - self._uutc_ss[e][0]) / 1e6)
                         * self._fs[e])
                stop = (((full_t_ss.stop - self._uutc_ss[e][0]) / 1e6)
                        * self._fs[e])
                step = ((full_t_ss.step / 1e6)
                        * self._fs[e])
                samps[i] = slice(int(start), int(stop), int(step))

        elif isinstance(t_ss, np.ndarray):
            samps = np.zeros(len(elements), object)
            if (np.ndim(t_ss) == 1) and (t_ss.dtype != object):
                for i, e in enumerate(elements):
                    self._check_time(e, t_ss.min())
                    self._check_time(e, t_ss.max())
                    samps[i] = (((t_ss - self._uutc_ss[e][0]) / 1e6)
                                * self._fs[e]).astype(int)
            elif np.ndim(t_ss) == 2:
                for i, e in enumerate(elements):
                    self._check_time(e, t_ss[e].min())
                    self._check_time(e, t_ss[e].max())
                    samps[i] = (((t_ss[e] - self._uutc_ss[e][0]) / 1e6)
                                * self._fs[e]).astype(int)
            elif (np.ndim(t_ss) == 1) and (t_ss.dtype == object):
                for i, (e, t) in enumerate(zip(elements, t_ss)):
                    self._check_time(e, t.start)
                    self._check_time(e, t.stop)
                    ts = self._create_full_slice(t, e)
                    start = (((ts.start - self._uutc_ss[e][0]) / 1e6)
                             * self._fs[e])
                    stop = (((ts.stop - self._uutc_ss[e][0]) / 1e6)
                            * self._fs[e])
                    step = ((ts.step / 1e6)
                            * self._fs[e])
                    samps[i] = slice(int(start), int(stop), int(step))

        return (elements, samps)

    def __len__(self):
        return len(self._mrb)

    def __repr__(self):
        return self._mrb.__repr__()

    def __str__(self):
        return self._mrb.__str__()

    def __getitem__(self, s):

        if isinstance(s, (int, slice, list, np.ndarray)):
            return self._mrb[s]

        elif isinstance(s, tuple):
            samp_s = self._uutc_to_samp(s)
            return self._mrb[samp_s[0], samp_s[1]]

        else:
            raise ValueError('Incorrect type "'+type(s).__name__+'" only'
                             ' integers, slices and arrays allowed')

    def __setitem__(self, s, val):

        # Assign one array to one element
        if isinstance(s, (int, slice, list, np.ndarray)):
            self._mrb[s] = val
            return

        # Assign array(s) to slices over element(s)
        elif isinstance(s, tuple):
            samp_s = self._uutc_to_samp(s)
            self._mrb[samp_s[0], samp_s[1]] = val

        else:
            raise ValueError('Incorrect type "'+type(s).__name__+'" only'
                             ' integers, slices and arrays allowed')
