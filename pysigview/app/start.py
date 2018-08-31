#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug  2 22:29:01 2017

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

This file will serve for doing stuff before we actually start the application.
Alternatively, it can parse command line arguments.
"""

# Std imports

# Third pary imports

# Local imports


def main():
    """
    Start pysigview application/
    """

    from pysigview.app import main_window
    main_window.main()


if __name__ == "__main__":
    main()
