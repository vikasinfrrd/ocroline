from __future__ import print_function

import os

from pylab import *
from scipy.ndimage import filters, interpolation


def autocrop0(image, threshold=1e-3, extra=2):
    bimage = image
    if image.ndim == 3:
        bimage = sum(bimage, 2)
    indexes = find(sum(bimage, 1) > threshold)
    lo = max(0, amin(indexes)-extra)
    hi = min(len(bimage), amax(indexes)+extra)
    return image[lo:hi]


def autocrop(image, extra=2):
    if image.ndim == 2:
        return autocrop0(autocrop0(image, extra=extra).transpose(1, 0),
                         extra=extra).transpose(1, 0)
    else:
        return autocrop0(autocrop0(image, extra=extra).transpose(1, 0, 2),
                         extra=extra).transpose(1, 0, 2)


def scale_to_h(img, target_height, order=1, dtype=dtype('f'), cval=0):
    h, w = img.shape
    scale = target_height * 1.0 / h
    target_width = int(scale * w)
    output = interpolation.affine_transform(1.0 * img, eye(2) / scale, order=order,
                                            output_shape=(
                                                target_height, target_width),
                                            mode='constant', cval=cval)
    output = array(output, dtype=dtype)
    return output


class CenterNormalizer:

    def __init__(self, target_height=48, params=(4, 1.0, 0.3)):
        self.debug = int(os.getenv("debug_center") or "0")
        self.target_height = target_height
        self.range, self.smoothness, self.extra = params

    def setHeight(self, target_height):
        self.target_height = target_height

    def measure(self, line):
        h, w = line.shape
        smoothed = filters.gaussian_filter(line, (h * 0.5, h * self.smoothness),
                                           mode='constant')
        smoothed += 0.001 * filters.uniform_filter(smoothed, (h * 0.5, w),
                                                   mode='constant')
        self.shape = (h, w)
        a = argmax(smoothed, axis=0)
        a = filters.gaussian_filter(a, h * self.extra)
        self.center = array(a, 'i')
        deltas = abs(arange(h)[:, newaxis] - self.center[newaxis, :])
        self.mad = mean(deltas[line != 0])
        self.r = int(1 + self.range * self.mad)
        if self.debug:
            figure("center")
            imshow(line, cmap=cm.gray)
            plot(self.center)
            ginput(1, 1000)

    def dewarp(self, img, cval=0, dtype=dtype('f')):
        assert img.shape == self.shape
        h, w = img.shape
        padded = vstack([cval * ones((h, w)), img, cval * ones((h, w))])
        center = self.center + h
        dewarped = [padded[center[i] - self.r:center[i] + self.r, i]
                    for i in range(w)]
        try:
            dewarped = array(dewarped, dtype=dtype).T
        except ValueError, e:
            print(e)
            return img
        return dewarped

    def normalize(self, img, order=1, dtype=dtype('f'), cval=0):
        dewarped = self.dewarp(img, cval=cval, dtype=dtype)
        h, w = dewarped.shape
        # output = zeros(dewarped.shape,dtype)
        scaled = scale_to_h(dewarped, self.target_height, order=order,
                            dtype=dtype, cval=cval)
        return scaled

    def measure_and_normalize(self, line):
        if line.ndim == 3:
            line = mean(line, 2)
        self.measure(line)
        return self.normalize(line)
