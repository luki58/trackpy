# Copyright 2012 Daniel B. Allan
# dallan@pha.jhu.edu, daniel.b.allan@gmail.com
# http://pha.jhu.edu/~dallan
# http://www.danallan.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or (at
# your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses>.

"""These functions generate handy plots."""

from functools import wraps
import numpy as np
import pandas as pd
from pandas import DataFrame, Series
import matplotlib as mpl
import matplotlib.pyplot as plt
import logging
import motion

logger = logging.getLogger(__name__)

def _make_axes(func):
    """
    A decorator for plotting functions.
    NORMALLY: Direct the plotting function to the current axes, gca().
              When it's done, make the legend and show that plot. 
              (Instant gratificaiton!)
    BUT:      If the uses passes axes to plotting function, write on those axes
              and return them. The user has the option to draw a more complex 
              plot in multiple steps.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'ax' not in kwargs:
            kwargs['ax'] = plt.gca()
            func(*args, **kwargs)
            if not kwargs['ax'].get_legend_handles_labels() == ([], []):
                plt.legend(loc='best')
            plt.show()
        else:
            return func(*args, **kwargs)
    return wrapper

def _make_fig(func):
    """See _make_axes."""
    wraps(func)
    def wrapper(*args, **kwargs):
        if 'fig' not in kwargs:
            kwargs['fig'] = plt.gcf()
            func(*args, **kwargs)
            plt.show()
        else:
            return func(*args, **kwargs)
    return wrapper

@_make_axes
def plot_traj(traj, colorby='probe', mpp=1, label=False, superimpose=None, 
       cmap=mpl.cm.winter, ax=None):
    """Plot traces of trajectories for each probe.
    Optionally superimpose it on a frame from the video.

    Parameters
    ----------
    traj : DataFrame including columns x and y
    colorby: {'probe', 'frame'}
    mpp : microns per pixel
    superimpose : filepath of background image, default None
    cmap : This is only used in colorby='frame' mode.
        Default = mpl.cm.winter
    ax : matplotlib axes object, defaults to current axes

    Returns
    -------
    None
    """
    # Axes labels
    if superimpose or mpp == 1:
        logger.warning("Using units of px, not microns")
        ax.set_xlabel('x [px]')
        ax.set_ylabel('y [px]')
    else:
        ax.set_xlabel('x [um]')
        ax.set_ylabel('y [um]')
    # Background image
    if superimpose:
        image = 1-plt.imread(superimpose)
        ax.imshow(image, cmap=plt.cm.gray)
        ax.set_xlim(0, image.shape[1])
        ax.set_ylim(0, image.shape[0])
    # Trajectories
    if colorby == 'probe':
        # Unstack probes into columns.
        unstacked = traj.set_index(['frame', 'probe']).unstack()
        ax.plot(mpp*unstacked['x'], mpp*unstacked['y'])
    if colorby == 'frame':
        # Read http://www.scipy.org/Cookbook/Matplotlib/MulticoloredLine 
        from matplotlib.collections import LineCollection
        x = traj.set_index(['frame', 'probe'])['x'].unstack()
        y = traj.set_index(['frame', 'probe'])['y'].unstack()
        color_numbers = traj['frame'].values/float(traj['frame'].max())
        logger.info("Drawing multicolor lines takes awhile. "
                    "Come back in a minute.")
        for probe in x:
            points = np.array(
                [x[probe].values, y[probe].values]).T.reshape(-1, 1, 2)
            segments = np.concatenate([points[:-1], points[1:]], axis=1)
            lc = LineCollection(segments, cmap=cmap)
            lc.set_array(color_numbers)
            ax.add_collection(lc)
            ax.set_xlim(x.apply(np.min).min(), x.apply(np.max).max())
            ax.set_ylim(y.apply(np.min).min(), y.apply(np.max).max())
    if label:
        unstacked = traj.set_index(['frame', 'probe'])[['x', 'y']].unstack()
        coords = unstacked.fillna(method='backfill').stack().ix[1]
        for probe_id, coord in coords.iterrows():
            plt.text(coord['x'], coord['y'], str(probe_id),
                     horizontalalignment='center',
                     verticalalignment='center')
    ax.invert_yaxis()
    return ax

ptraj = plot_traj # convenience alias

@_make_axes
def annotate(image, centroids, circle_size=170, invert=False, ax=None):
    """Mark identified features with white circles.
    
    Parameters
    ----------
    image : image object or string filepath
    centroids : DataFrame including columns x and y
    circle_size : size of circle annotations in matplotlib's annoying
        arbitrary units, default 170
    invert : If you give a filepath as the image, specify whether to invert
        black and white. Default True.
    ax : matplotlib axes object, defaults to current axes
    
    Returns
    ------
    axes
    """ 
    # The parameter image can be an image object or a filename.
    if isinstance(image, basestring):
        image = plt.imread(image)
    if invert:
        ax.imshow(1-image, origin='upper', shape=image.shape, cmap=plt.cm.gray)
    else:
        ax.imshow(image, origin='upper', shape=image.shape, cmap=plt.cm.gray)
    ax.set_xlim(0, image.shape[1])
    ax.set_ylim(0, image.shape[0])
    ax.scatter(centroids['x'], centroids['y'], 
               s=circle_size, facecolors='none', edgecolors='g')
    return ax

@_make_axes
def mass_ecc(f, ax=None):
    """Plot each probe's mass versus eccentricity."""
    ax.plot(f['mass'], f['ecc'], 'ko', alpha=0.3)
    ax.set_xlabel('mass')
    ax.set_ylabel('eccentricity (0=circular)')
    return ax

@_make_axes
def mass_size(f, ax=None):
    """Plot each probe's mass versus size."""
    ax.plot(f['mass'], f['size'], 'ko', alpha=0.3)
    ax.set_xlabel('mass')
    ax.set_ylabel('size')
    return ax

@_make_axes
def subpx_bias(f, ax=None):
    """Histogram the fractional part of the x and y position.

    Notes
    -----
    If subpixel accuracy is good, this should be flat. If it depressed in the
    middle, try using a larger value for feature diameter."""
    f[['x', 'y']].applymap(lambda x: x % 1).hist(ax=ax)
    return ax

@_make_axes
def fit(data, fits, inverted_model=False, logx=False, logy=False, ax=None):
    data.dropna().plot(style='o', logx=logx, logy=logy, ax=ax)
    datalines = ax.get_lines() 
    if not inverted_model:
        fitlines = ax.plot(fits.index, fits)
    else:
        fitlines = ax.plot(fits.reindex(data.dropna().index), data.dropna())
    # Restrict plot axis to domain of the data, not domain of the fit.
    xmin = data.index.values[data.index.values > 0].min() if logx \
        else data.index.values.min()
    ax.set_xlim(xmin, data.index.values.max())
    # Match colors of data and corresponding fits.
    [f.set_color(d.get_color()) for d, f in zip(datalines, fitlines)]
    if logx:
        ax.set_xscale('log') # logx kwarg does not always take. Bug?
    return ax

@_make_axes
def plot_principal_axes(img, x_bar, y_bar, cov, ax=None):
    """Plot bars with a length of 2 stddev along the principal axes.

    Attribution
    -----------
    This function is based on a solution by Joe Kington, posted on Stack
    Overflow at http://stackoverflow.com/questions/5869891/
    how-to-calculate-the-axis-of-orientation/5873296#5873296
    """
    def make_lines(eigvals, eigvecs, mean, i):
        """Make lines a length of 2 stddev."""
        std = np.sqrt(eigvals[i])
        vec = 2 * std * eigvecs[:,i] / np.hypot(*eigvecs[:,i])
        x, y = np.vstack((mean-vec, mean, mean+vec)).T
        return x, y
    mean = np.array([x_bar, y_bar])
    eigvals, eigvecs = np.linalg.eigh(cov)
    ax.plot(*make_lines(eigvals, eigvecs, mean, 0), marker='o', color='white')
    ax.plot(*make_lines(eigvals, eigvecs, mean, -1), marker='o', color='red')
    ax.imshow(img)

def examine_jumps(data, jumps):
    fig, axes = plt.subplots(len(jumps), 1)
    for i, jump in enumerate(jumps):
        roi = data.ix[jump-10:jump+10]
        axes[i].plot(roi.index, roi, 'g.')
        axes[i].plot(jump, data[jump], 'ko')
    fig.show()
