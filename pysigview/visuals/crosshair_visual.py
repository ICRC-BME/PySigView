#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 12 23:15:47 2018

Crosshair visual

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

from vispy.visuals.infinite_line import InfiniteLineVisual
from vispy.visuals.visual import CompoundVisual
from vispy.scene.visuals import create_visual_node


class CrosshairVisual(CompoundVisual):

    def __init__(self, pos=None, color=(1.0, 1.0, 1.0, 1.0)):

        self._vline = InfiniteLineVisual(vertical=True)
        self._hline = InfiniteLineVisual(vertical=False)

        CompoundVisual.__init__(self, [self._vline, self._hline])

        self.set_data(pos, color)

    def set_data(self, pos=None, color=None):

        if pos is None:
            self._vline.set_data(pos, color)
            self._hline.set_data(pos, color)
        else:
            self._vline.set_data(pos[0], color)
            self._hline.set_data(pos[1], color)

        self.update()


Crosshair = create_visual_node(CrosshairVisual)
