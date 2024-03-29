# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""Module that provides a GUI-based editor for matplotlib's figure options"""

from pydeelib.widgets.formlayout import fedit

LINESTYLES = {
              '-': 'Solid',
              '--': 'Dashed',
              '-.': 'DashDot',
              ':': 'Dotted',
              'steps': 'Steps',
              'none': 'None',
              }

MARKERS = {
           'none': 'None',
           'o': 'circles',
           '^': 'triangle_up',
           'v': 'triangle_down',
           '<': 'triangle_left',
           '>': 'triangle_right',
           's': 'square',
           '+': 'plus',
           'x': 'cross',
           '*': 'star',
           'D': 'diamond',
           'd': 'thin_diamond',
           '1': 'tripod_down',
           '2': 'tripod_up',
           '3': 'tripod_left',
           '4': 'tripod_right',
           'h': 'hexagon',
           'H': 'rotated_hexagon',
           'p': 'pentagon',
           '|': 'vertical_line',
           '_': 'horizontal_line',
           '.': 'dots',
           }

COLORS = {'b': '#0000ff', 'g': '#00ff00', 'r': '#ff0000', 'c': '#ff00ff',
          'm': '#ff00ff', 'y': '#ffff00', 'k': '#000000', 'w': '#ffffff'}

def col2hex(color):
    """Convert matplotlib color to hex"""
    return COLORS.get(color, color)

def figure_edit(canvas, parent=None):
    """Edit matplotlib figure options"""
    axes = canvas.axes
    sep = (None, None) # separator
    
    has_curve = len(axes.get_lines())>0
    
    # Get / General
    xmin, xmax = axes.get_xlim()
    ymin, ymax = axes.get_ylim()
    general = [('Title', axes.get_title()),
               sep,
               (None, "<b>X-Axis</b>"),
               ('Min', xmin), ('Max', xmax),
               ('Label', axes.get_xlabel()),
               ('Scale', [axes.get_xscale(), 'linear', 'log']),
               sep,
               (None, "<b>Y-Axis</b>"),
               ('Min', ymin), ('Max', ymax),
               ('Label', axes.get_ylabel()),
               ('Scale', [axes.get_yscale(), 'linear', 'log'])
               ]

    if has_curve:
        # Get / Curves
        linedict = {}
        for line in axes.get_lines():
            label = line.get_label()
            if label == '_nolegend_':
                continue
            linedict[label] = line
        curves = []
        linestyles = LINESTYLES.items()
        markers = MARKERS.items()
        curvelabels = sorted(linedict.keys())
        for label in curvelabels:
            line = linedict[label]
            curvedata = [
                         ('Label', label),
                         sep,
                         (None, '<b>Line</b>'),
                         ('Style', [line.get_linestyle()] + linestyles),
                         ('Width', line.get_linewidth()),
                         ('Color', col2hex(line.get_color())),
                         sep,
                         (None, '<b>Marker</b>'),
                         ('Style', [line.get_marker()] + markers),
                         ('Size', line.get_markersize()),
                         ('Facecolor', col2hex(line.get_markerfacecolor())),
                         ('Edgecolor', col2hex(line.get_markeredgecolor())),
                         ]
            curves.append([curvedata, label, ""])
        
    datalist = [(general, "Axes", "")]
    if has_curve:
        datalist.append((curves, "Curves", ""))
    result = fedit(datalist, title="Figure options", parent=parent)
    if result is None:
        return
    
    if has_curve:
        general, curves = result
    else:
        general, = result
        
    # Set / General
    title, xmin, xmax, xlabel, xscale, ymin, ymax, ylabel, yscale = general
    axes.set_xscale(xscale)
    axes.set_yscale(yscale)
    axes.set_title(title)
    axes.set_xlim(xmin, xmax)
    axes.set_xlabel(xlabel)
    axes.set_ylim(ymin, ymax)
    axes.set_ylabel(ylabel)
    
    if has_curve:
        # Set / Curves
        for index, curve in enumerate(curves):
            line = linedict[curvelabels[index]]
            label, linestyle, linewidth, color, \
                marker, markersize, markerfacecolor, markeredgecolor = curve
            line.set_label(label)
            line.set_linestyle(linestyle)
            line.set_linewidth(linewidth)
            line.set_color(color)
            if marker is not 'none':
                line.set_marker(marker)
                line.set_markersize(markersize)
                line.set_markerfacecolor(markerfacecolor)
                line.set_markeredgecolor(markeredgecolor)
        
    # Redraw
    canvas.draw()
    