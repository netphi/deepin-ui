/* Copyright (C) 2011 Deepin, Inc.
 *               2011 Wang Yong
 *
 * Author:     Wang Yong <lazycat.manatee@gmail.com>
 * Maintainer: Wang Yong <lazycat.manatee@gmail.com>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <string.h>
#include <glib.h>
#include <Python.h>
#include "pygobject.h"
#include <cairo/cairo.h>
#include <pycairo/pycairo.h>
#include <stdlib.h>
#include <math.h>
#include <stdint.h>
#include <memory.h>
#include <stdio.h>

static void blur_image_surface (cairo_surface_t *surface, double radius);
static PyObject* dtk_cairo_blur_gaussian_blur(PyObject* self, PyObject* args);

static PyMethodDef cairo_blur_methods[] = {
     {"gaussian_blur", dtk_cairo_blur_gaussian_blur, METH_VARARGS,
      "Perform a gaussian blur of the specified radius on a cairo surface"},
     {NULL, NULL, 0, NULL}
};


struct _pixel
{
     guint64 alpha;
     guint64 red;
     guint64 green;
     guint64 blue;
};

static int *_calc_kernel (double sigma, int *size);
static void _apply_kernel (cairo_surface_t *surface, const int *kernel, int kernel_size);
static inline int _pos_to_index (int x, int y, int width, int height);
static inline struct _pixel _num_to_pixel_with_factor (guint32 value, int factor);
static inline guint32 _pixel_to_num_with_divisor (struct _pixel *pixel, int divisor);
static inline void _pixel_plus (struct _pixel *adder_sum, const struct _pixel *adder2);

PyMODINIT_FUNC initdtk_cairo_blur(void) {
     PyObject *m;

     /* This is necessary step for Python binding, otherwise got sefault error */
     init_pygobject();
     
     m = Py_InitModule("dtk_cairo_blur", cairo_blur_methods);

     if (!m) {
          return;
     }
}


static PyObject* dtk_cairo_blur_gaussian_blur(PyObject* self, PyObject* args) {
     PycairoSurface* surface = NULL;
     double radius = 0;

     if (!PyArg_ParseTuple(args, "Od", &surface, &radius)) {
          return NULL;
     }

     blur_image_surface(surface->surface, radius);

     Py_RETURN_NONE;
}

static inline int
_pos_to_index (int x, int y, int width, int height) {
     if (x >= width || y >= height || x < 0 || y < 0)
          return -1;
     return y * width + x;
}

static inline struct _pixel
_num_to_pixel_with_factor (guint32 value, int factor) {
     /* This only works for type CAIRO_FORMAT_ARGB32 */
     struct _pixel pixel;
     pixel.alpha = ((value >> 24) & 0xff) * factor;
     pixel.red = ((value >> 16) & 0xff) * factor;
     pixel.green = ((value >> 8) & 0xff) * factor;
     pixel.blue = (value & 0xff) * factor;
     return pixel;
}

static inline guint32
_pixel_to_num_with_divisor (struct _pixel *pixel, int divisor) {
     guint32 alpha = pixel->alpha / divisor;
     if (alpha > 0xff) alpha = 0xff;
     guint32 red = pixel->red / divisor;
     if (red > 0xff) red = 0xff;
     guint32 green = pixel->green / divisor;
     if (green > 0xff) green = 0xff;
     guint32 blue = pixel->blue / divisor;
     if (blue > 0xff) blue = 0xff;
     return (alpha << 24) | (red << 16) | (green << 8) | blue;
}

static inline void
_pixel_plus (struct _pixel *adder_sum, const struct _pixel *adder2) {
     adder_sum->alpha += adder2->alpha;
     adder_sum->red += adder2->red;
     adder_sum->green += adder2->green;
     adder_sum->blue += adder2->blue;
}

static int *
_calc_kernel (double sigma, int *size) {
     int kernel_size = ceil (sigma * 6);
     if (kernel_size % 2 == 0)
          kernel_size++;
     int orig = kernel_size / 2;
     if (size) *size = kernel_size;
     double *kernel_double = g_new (double, kernel_size);
     double sum = 0.0;
     int *kernel = g_new (int, kernel_size);
     int i;
     double factor = 1.0 / sqrt (2.0 * M_PI * sigma * sigma);
     double denom = 1.0 / (2.0 * sigma * sigma);
     for (i = 0; i < kernel_size; i++)
     {
          kernel_double[i] = factor * exp (- (i - orig) * (i - orig) * denom);
          sum += kernel_double[i];
     }
     /* convert to pixed point number */
     for (i = 0; i < kernel_size; i++)
     {
          kernel[i] = kernel_double[i] / sum * (1 << (sizeof (int) / 2 * 8));
     }
     g_free (kernel_double);
     return kernel;
}

static void _apply_kernel (cairo_surface_t *surface, const int *kernel, int kernel_size) {
     static const int DIR[2][2] = {{0, 1}, {1, 0}};
     guint32 *pixels = (guint32*) cairo_image_surface_get_data (surface);
     int width = cairo_image_surface_get_width (surface);
     int height = cairo_image_surface_get_height (surface);
     int kernel_orig = kernel_size / 2;
     int d, i, x, y;
     for (d = 0; d < 2; d++)
     {
          guint32 *old_pixels = g_new (guint32, width * height);
          memcpy (old_pixels, pixels, sizeof (guint32) * width * height);
          for (x = 0; x < width; x++)
               for (y = 0; y < height; y++)
               {
                    struct _pixel final_value = {0};
                    int sum = 0;
                    for (i = 0; i < kernel_size; i++)
                    {
                         int x1 = x + (i - kernel_orig) * DIR[d][0];
                         int y1 = y + (i - kernel_orig) * DIR[d][1];
                         int index1 = _pos_to_index (x1, y1, width, height);
                         if (index1 > 0)
                         {
                              sum += kernel[i];
                              struct _pixel value = _num_to_pixel_with_factor (old_pixels[index1],
                                                                               kernel[i]);
                              _pixel_plus (&final_value, &value);
                         }
                    }
                    int index = _pos_to_index (x, y, width, height);
                    pixels[index] = _pixel_to_num_with_divisor (&final_value, sum);
               }
          g_free (old_pixels);
     }
}

static void blur_image_surface (cairo_surface_t *surface, double sigma) {
     int kernel_size;
     int *kernel = _calc_kernel (sigma, &kernel_size);
     _apply_kernel (surface, kernel, kernel_size);
     g_free (kernel);
}
