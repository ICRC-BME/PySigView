#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug  3 15:33:32 2017

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
from vispy.scene import PanZoomCamera, BaseCamera
from vispy.geometry import Rect

# Local imports


class NavigationCamera(PanZoomCamera):

    def __init__(self, bar_view):
        super(NavigationCamera, self).__init__()

        self.bar_view = bar_view

#    def viewbox_mouse_event(self,event):
#
#        if event.handled or not self.interactive:
#            return
#
#        BaseCamera.viewbox_mouse_event(self, event)
#
#        modifiers = event.mouse_event.modifiers
#
#        if event.mouse_event.button == 1 and not modifiers:
#            self.bar_view.set_location(event.mouse_event.pos)

    def limit_zoom(self, rect):
        if rect.left < 0:
            rect.left = 0
        if rect.right > 1:
            rect.right = 1
        if rect.bottom < 0:
            rect.bottom = 0
        if rect.top > 1:
            rect.top = 1

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

    def viewbox_mouse_event(self, event):
        """ViewBox mouse event handler

        Parameters
        ----------
        event : instance of Event
            The mouse event.
        """
        # When the attached ViewBox reseives a mouse event, it is sent to the
        # camera here.

        print(event)

        if event.handled or not self.interactive:
            return

        # Scrolling
        BaseCamera.viewbox_mouse_event(self, event)

        if event.type == 'mouse_wheel':
            center = self._scene_transform.imap(event.pos)
            self.zoom((1 + self.zoom_factor) ** (-event.delta[1] * 30), center)
            event.handled = True

        elif event.type == 'mouse_move':
            if event.press_event is None:
                return

            modifiers = event.mouse_event.modifiers

            if 2 in event.buttons and not modifiers:
                # Zoom
                p1c = np.array(event.last_event.pos)[:2]
                p2c = np.array(event.pos)[:2]
                scale = ((1 + self.zoom_factor) **
                         ((p1c-p2c) * np.array([1, -1])))
                center = self._transform.imap(event.press_event.pos[:2])
                self.zoom(scale, center)
                event.handled = True
            else:
                event.handled = False
        elif event.type == 'mouse_press':
            if event.mouse_event.button == 1:
                self.bar_view.set_location(event.pos)
            event.handled = event.button in [1, 2]
        else:
            event.handled = False
