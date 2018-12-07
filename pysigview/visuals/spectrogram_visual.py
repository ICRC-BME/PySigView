#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov 23 12:02:26 2018

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

# Third party imports
import numpy as np

from vispy.visuals.image import ImageVisual
from vispy.util.fourier import stft, fft_freqs
from vispy.ext.six import string_types
from vispy.scene.visuals import create_visual_node

# Local imports


class SpectrogramVisual(ImageVisual):
    """Calculate and show a spectrogram
    Parameters
    ----------
    x : array-like
        1D signal to operate on. ``If len(x) < n_fft``, x will be
        zero-padded to length ``n_fft``.
    n_fft : int
        Number of FFT points. Much faster for powers of two.
    step : int | None
        Step size between calculations. If None, ``n_fft // 2``
        will be used.
    fs : float
        The sample rate of the data.
    window : str | None
        Window function to use. Can be ``'hann'`` for Hann window, or None
        for no windowing.
    color_scale : {'linear', 'log'}
        Scale to apply to the result of the STFT.
        ``'log'`` will use ``10 * log10(power)``.
    cmap : str
        Colormap name.
    clim : str | tuple
        Colormap limits. Should be ``'auto'`` or a two-element tuple of
        min and max values.
    """
    def __init__(self, x=None, n_fft=256, step=None, fs=1., window='hann',
                 color_scale='log', cmap='cubehelix', clim='auto',
                 normalize=False):

        self._x = x
        self._n_fft = int(n_fft)
        self._step = step
        self._fs = float(fs)
        self._window = window
        self._color_scale = color_scale
        self._cmap = cmap
        self._clim = clim
        self._normalize = normalize

        self._clim_auto = True

        if not isinstance(color_scale, string_types) or \
                color_scale not in ('log', 'linear'):
            raise ValueError('color_scale must be "linear" or "log"')

        super(SpectrogramVisual, self).__init__(clim=clim, cmap=cmap)
        self._update_image()

    @property
    def freqs(self):
        """The spectrogram frequencies"""
        return fft_freqs(self._n_fft, self._fs)

    @property
    def data(self):
        return self._data

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, x):
        self._x = x
        self._update_image()

    @property
    def n_fft(self):
        return self._n_fft

    @n_fft.setter
    def n_fft(self, n_fft):
        self._n_fft = int(n_fft)
        self._update_image()

    @property
    def step(self):
        if self._step is None:
            return self._n_fft // 2
        else:
            return self._step

    @step.setter
    def step(self, step):
        self._step = step
        self._update_image()

    @property
    def fs(self):
        return self._fs

    @fs.setter
    def fs(self, fs):
        self._fs = fs
        self._update_image()

    @property
    def window(self):
        return self._window

    @window.setter
    def window(self, window):
        self._window = window
        self._update_image()

    @property
    def color_scale(self):
        return self._color_scale

    @color_scale.setter
    def color_scale(self, color_scale):
        if not isinstance(color_scale, string_types) or \
                color_scale not in ('log', 'linear'):
            raise ValueError('color_scale must be "linear" or "log"')
        self._color_scale = color_scale
        self._update_image()

    @property
    def normalize(self):
        return self._normalize

    @normalize.setter
    def normalize(self, normalize):
        self._normalize = normalize
        self._update_image()

    # Override Image clim since for now before it is fixed in main repo
    @property
    def clim(self):
        return (self._clim if isinstance(self._clim, string_types) else
                tuple(self._clim))

    @clim.setter
    def clim(self, clim):
        if isinstance(clim, string_types):
            if clim != 'auto':
                raise ValueError('clim must be "auto" if a string')
            self._clim_auto = True
        else:
            clim = np.array(clim, float)
            if clim.shape != (2,):
                raise ValueError('clim must have two elements')
            self._clim_auto = False
        self._clim = clim
        self._need_texture_upload = True
        self.update()

    def _update_image(self):
        if self._x is not None:
            data = stft(self._x, self._n_fft, self._step, self._fs,
                        self._window)
            data = np.abs(data)
            data = 20 * np.log10(data) if self._color_scale == 'log' else data
            if self._normalize:
                for i in range(data.shape[0]):
                    data[i, :] -= np.mean(data[i, :])
                    data[i, :] /= np.std(data[i, :])
            self.set_data(data)
            self.update()
            if self._clim_auto:
                self.clim = 'auto'


Spectrogram = create_visual_node(SpectrogramVisual)
