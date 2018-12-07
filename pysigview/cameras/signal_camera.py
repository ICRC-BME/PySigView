#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 22 13:14:09 2017

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
import numpy as np

# Local imports
from vispy.scene import Magnify1DCamera
from vispy.geometry import Rect


class SignalCamera(Magnify1DCamera):
    """
    Reimplemented Vispy PanZoomCamera
    """

    def __init__(self):
        super(SignalCamera, self).__init__(mag=1)

        self._limit_rect = Rect(0, 0, 1, 1)

    @property
    def limit_rect(self):
        return self._limit_rect

    @limit_rect.setter
    def limit_rect(self, args):
        if isinstance(args, tuple):
            rect = Rect(*args)
        elif args is None:
            rect = Rect(-np.inf, -np.inf, np.inf, np.inf)
        else:
            rect = Rect(args)

        if self._limit_rect != rect:
            self._limit_rect = rect

    def limit_zoom(self, rect):
        if rect.left < self._limit_rect.left:
            rect.left = self._limit_rect.left
        if rect.right > self._limit_rect.right:
            rect.right = self._limit_rect.right
        if rect.bottom < self._limit_rect.bottom:
            rect.bottom = self._limit_rect.bottom
        if rect.top > self._limit_rect.top:
            rect.top = self._limit_rect.top

    def limit_pan(self, pan):
        if self.rect.left <= self._limit_rect.left and pan[0] < 0:
            pan[0] = 0

        if self.rect.right >= self._limit_rect.right and pan[0] > 0:
            pan[0] = 0

        if self.rect.bottom <= self._limit_rect.bottom and pan[1] < 0:
            pan[1] = 0

        if self.rect.top >= self._limit_rect.top and pan[1] > 0:
            pan[1] = 0

    def scale_magnification(self, scale):
        """
        Changes the radius of magnification glass
        """

        self.size_factor += sum(scale-1)*-0.5

        if self.size_factor > 0.5:
            self.size_factor = 0.5
        elif self.size_factor < 0.05:
            self.size_factor = 0.05

        self.view_changed()

        return

    # ---- Vispy reimplementations -----

    def zoom(self, factor, center=None):
        """ Zoom in (or out) at the given center

        Parameters
        ----------
        factor : float or tuple
            Fraction by which the scene should be zoomed (e.g. a factor of 2
            causes the scene to appear twice as large).
        center : tuple of 2-4 elements
            The center of the view. If not given or None, use the
            current center.
        """
        assert len(center) in (2, 3, 4)
        # Get scale factor, take scale ratio into account
        if np.isscalar(factor):
            scale = [factor, factor]
        else:
            if len(factor) != 2:
                raise TypeError("factor must be scalar or length-2 sequence.")
            scale = list(factor)
        if self.aspect is not None:
            scale[0] = scale[1]

        # Init some variables
        center = center if (center is not None) else self.center
        # Make a new object (copy), so that allocation will
        # trigger view_changed:
        rect = Rect(self.rect)
        # Get space from given center to edges
        left_space = center[0] - rect.left
        right_space = rect.right - center[0]
        bottom_space = center[1] - rect.bottom
        top_space = rect.top - center[1]
        # Scale these spaces
        rect.left = center[0] - left_space * scale[0]
        rect.right = center[0] + right_space * scale[0]
        rect.bottom = center[1] - bottom_space * scale[1]
        rect.top = center[1] + top_space * scale[1]

        self.limit_zoom(rect)

        self.rect = rect

    def pan(self, *pan):
        """Pan the view.

        Parameters
        ----------
        *pan : length-2 sequence
            The distance to pan the view, in the coordinate system of the
            scene.
        """

        if len(pan) == 1:
            pan = pan[0]

        self.limit_pan(pan)

        self.rect = self.rect + pan

    def viewbox_mouse_event(self, event):
        """ViewBox mouse event handler

        Parameters
        ----------
        event : instance of Event
            The mouse event.
        """
        # When the attached ViewBox reseives a mouse event, it is sent to the
        # camera here.

        if event.handled or not self.interactive:
            return

        modifiers = event.mouse_event.modifiers

        if not modifiers:
            if event.type == 'mouse_wheel':
                self.mouse_pos = event.pos[:2]
                # wheel rolled; adjust the magnification factor and hide the
                # event from the superclass
                m = self.mag_target
                m *= 1.2 ** event.delta[1]
                m = m if m > 1 else 1
                self.mag_target = m
            elif self.mag_target == 1:  # This menas the magnify mode is off
                # send everything _except_ wheel events to the superclass
                super(Magnify1DCamera, self).viewbox_mouse_event(event)
            else:

                if event.type == 'mouse_move':

                    if 1 in event.buttons and not modifiers:
                        self.mouse_pos = event.pos[:2]

                    if 2 in event.buttons and not modifiers:
                        # Changes size factor
                        p1c = np.array(event.last_event.pos)[:2]
                        p2c = np.array(event.pos)[:2]
                        scale = ((1 + self.zoom_factor) **
                                 ((p1c-p2c) * np.array([1, -1])))
                        self.scale_magnification(scale)
                        event.handled = True
                    else:
                        event.handled = False

                elif event.type == 'mouse_press':
                    if event.button == 1:
                        self.mouse_pos = event.pos[:2]
                    # accept the event if it is button 1 or 2.
                    # This is required in order to receive future events
                    event.handled = event.button in [1, 2]

            # start the timer to smoothly modify the transform properties.
            if not self.timer.running:
                if self.mouse_pos is None:
                    self.mouse_pos = event.pos[:2]
                self.timer.start()

            self._update_transform()
