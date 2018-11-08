#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug  3 18:30:29 2017

Definition of visual container - super class for data pieces shown in canvas

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
# Std imports

# Third pary imports
import numpy as np
from scipy.signal import butter, filtfilt

# Local imports


class BaseVisualContainer():
    def __init__(self, orig_channel):
        super(BaseVisualContainer, self).__init__()

        self.orig_channel = orig_channel
        self.add_channels = []  # For montages / connectivity
        self.fsamp = 0  # Duplicate of header info but keeps things neat
        self.ufact = 0  # Duplicate of header info but keeps things neat
        self.unit = ''  # Duplicate of header info but keeps things neat
        self.start_time = 0
        self.plot_position = [0, 0, 0]  # Not used [] coordinates - row, column
        self.uutc_ss = []
        self.container = None  # ??? Rename to container_item?
        self.data_array_pos = []
        self.visual = None

    def add_data_array_pos(self, position):
        self.data_array_pos.append(position)

    def del_data_array_pos(self, position):
        self.data_array_pos.pop(self.data_array_pos.index(position))


class SignalContainer(BaseVisualContainer):
    def __init__(self, orig_channel):
        super().__init__(orig_channel)

        self.scale_factor = 1
        self.autoscale = False
        self._line_color = None
        self._line_alpha = 1.
        self._visual_array_idx = 0
        self._data = None
        self._visible = True

        self.transform_chain = []

        # Exposed attributes [name, value, read only flag]
        self.exposed_attributes = [['Sampling frequency',
                                    self.fsamp, True],
                                   ['Voltage factor',
                                    self.ufact, True],
                                   ['Unit',
                                    self.unit, True],
                                   ['Plot position',
                                    self.plot_position, True],
                                   ['uUTC start/stop',
                                    self.uutc_ss, True],
                                   ['Time span(s)',
                                    np.diff(self.uutc_ss), False],
                                   ['Alpha',
                                    self.line_alpha, False],
                                   [self.unit+' per px',
                                    self.ufact*self.scale_factor, False]]

    @property
    def name(self):
        transform_names = [x.name for x in self.transform_chain]
        return(''.join([self.orig_channel] + transform_names))

    @property
    def line_alpha(self):
        return self._line_alpha

    @line_alpha.setter
    def line_alpha(self, alpha):
        self._line_alpha = alpha
        self.line_color = self._line_color

    @property
    def line_color(self):
        return self._line_color

    @line_color.setter
    def line_color(self, color):
        self._line_color = color

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        data = np.squeeze(np.vstack(data))

        # Apply transform chain
        if len(self.transform_chain):
            for t in self.transform_chain:
                data = t.apply_transform(data)

        if self.N is not None:
            data = self.subsample_data(data)

        self._data = data

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, visible):
        self._visible = visible

    def update_eas(self):
        # Exposed attributes [name, value, read only flag]
        self.exposed_attributes = [['Sampling frequency',
                                    self.fsamp, True],
                                   ['Unit factor',
                                    self.ufact, True],
                                   ['Unit',
                                    self.unit, True],
                                   ['Plot position',
                                    self.plot_position, True],
                                   ['uUTC start/stop',
                                    self.uutc_ss, True],
                                   ['Time span(s)',
                                    np.diff(self.uutc_ss)[0]/1e6, False],
                                   ['Alpha',
                                    self.line_alpha, False],
                                   [self.unit+' per px',
                                    self.ufact*self.scale_factor, False]]

    def set_eas(self, label, value):
        idx = [i for i, x in enumerate(self.exposed_attributes)
               if x[0] == label][0]
        # TODO - think of a better way to do this
        if idx == 5:
            uutc_span = float(value) * 1e6
            uutc_midpoint = np.sum(self.uutc_ss) / 2
            self.uutc_ss[0] = uutc_midpoint - uutc_span / 2
            self.uutc_ss[1] = uutc_midpoint + uutc_span / 2
        elif idx == 6:
            self.line_alpha = float(value)
        elif idx == 7:
            pass

    def transoform_chain_add(self, transform):
        if transform in self.transform_chain:
            return
        transform.modify_visual_container()
        self.transform_chain.append(transform)
        if self.container is not None:
            self.container.update_label()

    def transform_chain_remove(self, transform):
        self.transform_chain.pop(transform)
        if self.container is not None:
            self.container.update_label()

    def subsample_data(self, data):

        # TODO - consider using numpy.fft to get rid of scipy dependency

        data_len = np.size(data)
        if not data_len:
            return data

        pad = data_len % self.N

        if pad:
            data = data[:-pad]

        # Check if the data has nans
        data_nan = np.isnan(data)

        if self.N < np.size(data, 0):
            cut_off = self.N / (np.size(data, 0) * 2)
            b, a = butter(4, cut_off)
            if len(data[~data_nan]):
                # This will create edge artifacts!
                data[~data_nan] = filtfilt(b, a, data[~data_nan])
            # data[::int(len(data)/N)] # Downsampling by choosing one sample
            return np.nanmean(data.reshape([self.N,
                                            int(np.floor(data_len/self.N))]),
                              axis=1)
        elif self.N > np.size(data) and self.N < np.size(data) * 2:
            return np.nanmean(data.reshape([self.N,
                                            int(np.floor(data_len/self.N))]),
                              axis=1)
        else:
            return data
