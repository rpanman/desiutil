# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-
"""
==============
desiutil.brick
==============

Code for calculating bricks, which are a tiling of the sky with the following
properties:

- bricks form rows in dec like a brick wall; edges are constant RA or dec
- they are rectangular with longest edge shorter or equal to bricksize
- circles at the poles with diameter=bricksize
- there are an even number of bricks per row

Use this with caution!  In most cases you should be propagating brick
info from input targeting, not recalculating brick locations and names.

Note that this code was originally in desispec_, so earlier commit information
is in the desispec_ repository.
"""

from __future__ import absolute_import, division, print_function

import numpy as np

class Bricks(object):
    """The Bricks object describes bricks of a certain size.

    Parameters
    ----------
    bricksize : :class:`float`, optional
        Brick size in degrees.  Default 0.25 degrees.

    Attributes
    ----------
    bricksize
    """
    def __init__(self, bricksize=0.25):
        #- Brick row centers and edges
        center_dec = np.arange(-90.0, +90.0+bricksize/2, bricksize)
        edges_dec = np.arange(-90.0-bricksize/2, +90.0+bricksize, bricksize)
        # poles
        edges_dec[0] = -90.
        edges_dec[-1] = 90.

        nrow = len(center_dec)

        #- How many columns per row: even number, no bigger than bricksize
        ncol_per_row = np.zeros(nrow, dtype=int)
        for i in range(nrow):
            declo = np.abs(center_dec[i])-bricksize/2
            n = (360/bricksize * np.cos(declo*np.pi/180))
            ncol_per_row[i] = int(np.ceil(n/2)*2)

        #- special cases at the poles
        ncol_per_row[0] = 1
        ncol_per_row[-1] = 1

        #- ra
        center_ra = list()
        edges_ra = list()
        for i in range(nrow):
            edges = np.linspace(0, 360, ncol_per_row[i]+1)
            edges_ra.append( edges )
            center_ra.append( 0.5*(edges[0:-1]+edges[1:]) )
            # dra = edges[1]-edges[0]
            # center_ra.append(dra/2 + np.arange(ncol_per_row[i])*dra)

        #- More special cases at the poles
        edges_ra[0] = edges_ra[-1] = np.array([0, 360])
        center_ra[0] = center_ra[-1] = np.array([180,])

        #- Brick names [row, col]
        brickname = list()
        #ADM brick areas [row, col]
        brickarea = list()

        for i in range(nrow):
            #
            # This hack allows numbers like 39.599999999999994 to be
            # converted into 0396.
            #
            pm = 'p' if center_dec[i] >= 0 else 'm'
            dec = "{0:06.0f}".format(np.absolute(center_dec[i])*10000)
            names = list()
            for j in range(ncol_per_row[i]):
                ra = "{0:07.0f}".format(center_ra[i][j]*10000)
                names.append(ra[0:4]+pm+dec[0:3])
            brickname.append(names)
            #ADM integrate area factors between Dec edges and RA edges in degrees
            decfac = np.diff(np.degrees(np.sin(np.radians(edges_dec[i:i+2]))))
            rafac = np.diff(edges_ra[i])
            brickarea.append(list(rafac*decfac))

        self._bricksize = bricksize
        self._ncol_per_row = ncol_per_row
        self._brickname = brickname
        self._brickarea = brickarea
        self._center_dec = center_dec
        self._edges_dec = edges_dec
        self._center_ra = center_ra
        self._edges_ra = edges_ra
        self._brick_table = None

    def __repr__(self):
        return "Bricks(bricksize={0._bricksize:4.2f})".format(self)

    @property
    def bricksize(self):
        """Size of a brick in degrees.
        """
        return self._bricksize

    def _array_radec(self, ra, dec):
        """Convert (`ra`, `dec`) to arrays and clean up the data.
        """
        adec = np.atleast_1d(dec)
        ara = np.atleast_1d(ra) % 360
        return ara, adec

    def _row_col(self, ra, dec):
        """Determine the brick row and column, given `ra`, `dec`.
        """
        row = ((dec+90.0+self._bricksize/2)/self._bricksize).astype(int)
        return (row, (ra/360.0 * self._ncol_per_row[row]).astype(int))

    def brickname(self, ra, dec):
        """Return brick name of brick covering (`ra`, `dec`).

        Parameters
        ----------
        ra : :class:`float` or :class:`~numpy.ndarray`
            Right Ascension in degrees.
        dec : :class:`float` or :class:`~numpy.ndarray`
            Declination in degrees.

        Returns
        -------
        :class:`~numpy.ndarray`
            An array of strings containing the names.
        """
        ara, adec = self._array_radec(ra, dec)
        irow, icol = self._row_col(ara, adec)
        names = np.empty(len(ara), dtype='U8')
        for thisrow in set(irow):
            these = np.where(thisrow == irow)[0]
            names[these] = np.array(self._brickname[thisrow])[icol[these]]
        if np.isscalar(ra):
            return names[0]
        return names

    def brickid(self, ra, dec):
        """Return the BRICKID for a given location.

        Parameters
        ----------
        ra : :class:`float` or :class:`~numpy.ndarray`
            Right Ascension in degrees.
        dec : :class:`float` or :class:`~numpy.ndarray`
            Declination in degrees.

        Returns
        -------
        :class:`~numpy.ndarray`
            The legacysurvey BRICKID at the locations of interest.
        """
        ara, adec = self._array_radec(ra, dec)
        irow, icol = self._row_col(ara, adec)
        #ADM the total number of BRICKIDs at the START of a given row
        ncolsum = np.cumsum(np.append(0, self._ncol_per_row))
        #ADM the BRICKID is just the sum of the number of columns up until
        #ADM the row of interest, and the number of columns along that row
        #ADM accounting for the indexes of the columns starting at 0
        brickid = ncolsum[irow] + icol + 1
        if np.isscalar(ra):
            return brickid[0]
        return brickid

    def brickq(self, ra, dec):
        """Return the BRICKQ for a given location.

        Parameters
        ----------
        ra : :class:`float` or :class:`~numpy.ndarray`
            Right Ascension in degrees.
        dec : :class:`float` or :class:`~numpy.ndarray`
            Declination in degrees.

        Returns
        -------
        :class:`~numpy.ndarray`
            The legacysurvey BRICKQ at the locations of interest.
        """
        ara, adec = self._array_radec(ra, dec)
        irow, icol = self._row_col(ara, adec)
        brickq = (icol % 2) + (irow % 2)*2
        brickq[irow == 0] = 1
        if np.isscalar(ra):
            return brickq[0]
        return brickq

    def brickarea(self, ra, dec):
        """Return the area of the brick for a given location.

        Parameters
        ----------
        ra : :class:`float` or :class:`~numpy.ndarray`
            Right Ascension in degrees.
        dec : :class:`float` or :class:`~numpy.ndarray`
            Declination in degrees.

        Returns
        -------
        :class:`~numpy.ndarray`
            The areas of the bricks at the locations of interest.
        """
        ara, adec = self._array_radec(ra, dec)
        irow, icol = self._row_col(ara, adec)
        #ADM the list of areas to return
        areas = np.empty(len(ara), dtype='<f4')
        #ADM grab the areas from the class
        for row in set(irow):
            cols = np.where(row == irow)
            areas[cols] = np.array(self._brickarea[row])[icol[cols]]
        if np.isscalar(ra):
            return areas[0]
        return areas

    def brickvertices(self, ra, dec):
        """Return the vertices in RA/Dec of the brick that given locations lie in

        Parameters
        ----------
        ra : :class:`float` or :class:`~numpy.ndarray`
            Right Ascension in degrees.
        dec : :class:`float` or :class:`~numpy.ndarray`
            Declination in degrees.

        Returns
        -------
        :class:`~numpy.ndarray`
            The 4 vertices of the bricks at the locations of interest
            (an array with 4 columns of (RA, Dec) and ``len(ra)`` rows).

        Notes
        -----
        The vertices are ordered counter-clockwise from the minimum (RA, Dec).
        """
        ara, adec = self._array_radec(ra, dec)
        irow, icol = self._row_col(ara, adec)
        #ADM grab the edges from the class
        ramin, ramax = np.array([self._edges_ra[row][col:col+2]
                                 for row, col in zip(irow, icol)]).T
        decmin, decmax = self._edges_dec[irow], self._edges_dec[irow+1]
        vertices = np.reshape(np.vstack([ramin, decmin,
                                         ramax, decmin,
                                         ramax, decmax,
                                         ramin, decmax]).T,
                              (len(ara), 4, 2))
        #ADM return the vertex array with one less dimension if a scalar was passed
        if np.isscalar(ra):
            return vertices[0]
        return vertices

    def brick_radec(self, ra, dec):
        """Return center (ra,dec) of brick that contains input (`ra`, `dec`) [deg]

        Parameters
        ----------
        ra : :class:`float` or :class:`~numpy.ndarray`
            Right Ascension in degrees.
        dec : :class:`float` or :class:`~numpy.ndarray`
            Declination in degrees.

        Returns
        -------
        :class:`~numpy.ndarray`
            The centers of the bricks at the locations of interest.
        """
        ara, adec = self._array_radec(ra, dec)
        irow, icol = self._row_col(ara, adec)
        if np.isscalar(ra):
            xra = self._center_ra[irow][icol]
            xdec = self._center_dec[irow]
        else:
            xra = np.array([self._center_ra[i][j] for i,j in zip(irow, icol)])
            xdec = self._center_dec[irow]
        return xra, xdec

    def to_table(self):
        """Convert :class:`~desiutil.brick.Bricks` object into a
        :class:`~astropy.table.Table`.

        Returns
        -------
        :class:`astropy.table.Table`
            A table containing the brick data.
        """
        if self._brick_table is None:
            from astropy.table import Table
            dtype = [('BRICKNAME', 'U8'),
                     ('BRICKID', 'i4'),
                     ('BRICKQ', 'i2'),
                     ('BRICKROW', 'i4'),
                     ('BRICKCOL', 'i4'),
                     ('RA', 'f8'), ('DEC', 'f8'),
                     ('RA1', 'f8'), ('RA2', 'f8'),
                     ('DEC1', 'f8'), ('DEC2', 'f8'),
                     ('AREA', 'f8')]
            brick_dict = dict([(n[0], list()) for n in dtype])
            brick_id = 0
            for row in range(len(self._center_dec)):
                for col in range(len(self._center_ra[row])):
                    brick_id += 1
                    brick_dict['BRICKNAME'].append(self._brickname[row][col])
                    brick_dict['BRICKID'].append(brick_id)
                    if row == 0:
                        q = 1
                    else:
                        q = (col % 2) + (row % 2)*2
                    brick_dict['BRICKQ'].append(q)
                    brick_dict['BRICKROW'].append(row)
                    brick_dict['BRICKCOL'].append(col)
                    brick_dict['RA'].append(self._center_ra[row][col])
                    brick_dict['DEC'].append(self._center_dec[row])
                    brick_dict['RA1'].append(self._edges_ra[row][col])
                    brick_dict['DEC1'].append(self._edges_dec[row])
                    brick_dict['RA2'].append(self._edges_ra[row][col+1])
                    brick_dict['DEC2'].append(self._edges_dec[row+1])
                    brick_dict['AREA'].append(self._brickarea[row][col])
            brick_data = np.zeros((brick_id,), dtype=dtype)
            for n in dtype:
                brick_data[n[0]] = brick_dict[n[0]]
            self._brick_table = Table(brick_data,
                                meta={'bricksize': self._bricksize})
            for n in ('RA', 'DEC', 'RA1', 'RA2', 'DEC1', 'DEC2'):
                self._brick_table[n].unit = 'deg'
        return self._brick_table


_bricks = None

def brickname(ra, dec, bricksize=0.25):
    """Return brick name of brick covering (`ra`, `dec`).

    Parameters
    ----------
    ra : :class:`float` or :class:`~numpy.ndarray`
        Right Ascension in degrees.
    dec : :class:`float` or :class:`~numpy.ndarray`
        Declination in degrees.
    bricksize : :class:`float`, optional
        Brick size in degrees.  Default 0.25 degrees.

    Returns
    -------
    :class:`~numpy.ndarray`
        An array of strings containing the names.

    Notes
    -----
    This function is a convenience wrapper on
    :meth:`desiutil.brick.Bricks.brickname`.  It will cache the brick
    computation to speed up repeated calls.
    """
    global _bricks
    if _bricks is None or _bricks.bricksize != bricksize:
        _bricks = Bricks(bricksize=bricksize)

    return _bricks.brickname(ra, dec)
