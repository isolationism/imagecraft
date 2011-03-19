#!/usr/bin/python

__author__ = 'kevin@isolationism.com'

# Standard library
import os
from warnings import warn

# Third-party libraries
from PIL import Image, ImageOps
from clevercss.consts import COLORS


class ImageGenerator(object):
    """
    A superclass for generating new images.

    Usage:

    1. Create an alpha-transparent greyscale image for each layer you wish
       to generate, and save to a separate filename. Make sure all layer
       images follow the same dimensions or else you'll have unpredictable
       results.

    2. Create a subclass of this class and define layers like so:

        layers = (
            {'my_blue': 'greyscale_image_to_tint_blue.png'},
            {'my_orange': 'greyscale_image_to_tint_orange.png'},
            ...
        )

    Note: layers are processed in the order in which they are presented. In
    this example, "my_orange" will be sandwiched on top of "my_blue".

    3. Define an output filename to generate to:

        output_filename = 'my_generated_image.png'

    4. Instantiate your new subclass with a dictionary of color values that map
       to all the color variables used in your layers:

        gc = MyGeneratorClass({'my_blue': (0,0,128), 'my_orange': (256,128,0)})

    5. Call the render method to generate the image and output to disk:

        gc.render()

    Note: Since you probably want to control where the generated images go,
    you may wish to supply an output_path argument to the constructor to
    specify where to save the file to. By default output will go to the
    'generated_images' folder.
    """

    # Override this property with your layer definitions.
    layers = ()
    output_filename = None
    _default_source_path = os.path.join(os.path.dirname(__file__),
                                        'source_images')
    _default_output_path = os.path.join(os.path.dirname(__file__),
                                        'generated_images')
    image_format = None

    def __init__(self, color_dict, source_path=None, output_path=None):
        """
        Constructor.

        color_dict - A dictionary-like object containing a mapping of variable
            names to corresponding color values.

        source_path - (optional) The path where the source files (specified in
            layers) will be read from. If none is provided, the
            _default_source_path will be used.

        output_path - (optional) The path where the generated file will be
            written. If none is provided, the _default_output_path will be
            used.
        """
        self.colors_for_layers = self._map_colors_to_layers(color_dict)
        self.source_path = source_path or self._default_source_path
        self.output_path = output_path or self._default_output_path

    def _map_colors_to_layers(self, color_dict):
        """
        Passes through all layers ensuring that a passed color maps to it.

        * Raises KeyError if the layer requires a color value that is not
          present in color_dict.
        * Raises TypeError if color_dict is not a dictionary-like object.
        * Raises TypeError if each layer in the layers constant is not a
          dictionary-like object.
        * Raises ValueError if each layer does not contain exactly one
          key-value pair.
        """
        if not hasattr(color_dict, 'keys'):
            raise TypeError, "color_dict must be a dictionary-like object"

        colors_for_layers = []

        for layer in self.layers:
            if not hasattr(layer, 'keys'):
                raise TypeError, "Each layer must be represented"
            else:
                if len(layer.keys()) != 1:
                    raise ValueError, "Each layer must have exactly one key-" \
                        "value pair"
                else:
                    required_color = layer.keys()[0]
                    if required_color not in color_dict.keys():
                        raise ValueError, "Required color %s not found in " \
                            "color_dict" % (required_color,)
                    else:
                        # Success; map the color to the image
                        found_color = self._rgbcolor(color_dict.get( \
                            required_color))
                        layer_img = layer.values()[0]
                        colors_for_layers.append({found_color: layer_img})

        return tuple(colors_for_layers)

    def _rgbcolor(self, colorval):
        """
        Attempts to translate the passed color into a returned RGB tuple.

        * Raises ValueError if it cannot handle the requested color.
        """
        colortup = (0,0,0) # Default value to start with

        # Handles hex triplets (most common case)
        if colorval.find('#') is 0:

            # 24-bit hexadecimal colors (e.g. #FF0000)
            if len(colorval) == 7:
                colortup = (
                    int(colorval[1:3], base=16),
                    int(colorval[3:5], base=16),
                    int(colorval[5:7], base=16),
                )

            # 12-bit hexadecimal colors (e.g. #F00)
            elif len(colorval) == 4:
                colortup = (
                    int(colorval[1:2]*2, base=16),
                    int(colorval[2:3]*2, base=16),
                    int(colorval[3:4]*2, base=16),
                )

        # Handles an RGB triplet (e.g. rgb(255, 0, 0))
        elif colorval.lower().find('rgb') is 0:
            colorval = colorval.replace('rgb', '').replace('(', '')\
                .replace(')', '')

            # Handles a percentage triplet
            if colorval.find('%') > -1:
                triplet = colorval.split(',')

                # Remove '%' symbol and surrounding whitespace
                triplet = tuple([x.replace('%', '').strip() for x in triplet])

                # Convert string/unicode to float
                triplet = tuple([float(x) for x in triplet])
                
                # Convert percentage float to 8-bit decimal
                colortup = tuple([int((x/100.0) * 255) for x in triplet])

            # Handles a binary triplet
            else:
                triplet = colorval.split(',')
                colortup = tuple([x.strip for x in triplet])

        # Handles named colors; requires recursion (e.g. "red")
        elif colorval in COLORS.keys():
            return self._rgbcolor(named_colors.get(colorval))
        
        # Unknown color format; throw an error
        else:
            raise ValueError, "I don't know how to handle colors in format %s" \
                % (colorval,)

        return colortup

    def render(self):
        """
        Passes over each layer, reads the file, colorizes it, sandwiches them
        all together, and saves.

        * Raises IOError if there's a problem reading or writing files.
        """
        baselayer = None

        for layeridx, layer in enumerate(self.colors_for_layers):
            color = layer.keys()[0]
            filename = layer.values()[0]
            img = Image.open(os.path.join(self.source_path, filename))
            img.load() # Explicitly load the image to prevent errors

            # Grab the alpha channel
            split_channels = img.split()
            if len(split_channels) == 2: # Image is greyscale + alpha
                alpha = split_channels[1]
            elif len(split_channels) == 4: # Image is RGB + A
                alpha = split_channels[3]
            else: # No alpha channel present
                alpha = None

            # Convert the image to greyscale in case it isn't already.
            greyscale_img = ImageOps.grayscale(img)

            # Colorize the image with `color` for black and `#FFF` for white
            white = (255, 255, 255)
            colorized = ImageOps.colorize(greyscale_img, color, white)

            # Split the colorized image into component channels
            bands_rgb = colorized.split()

            # Create a new image comprised of the component channels + alpha
            if alpha:
                bands_comb = Image.merge("RGBA", (bands_rgb[0], bands_rgb[1],
                                                        bands_rgb[2], alpha))
            else:
                bands_comb = Image.merge("RGB", (bands_rgb[0], bands_rgb[1],
                                                        bands_rgb[2]))

            if layeridx is 0:
                # Store the base layer
                baselayer = bands_comb
            else:
                if not alpha:
                    warn("Non-background layer %s has no alpha channel, " \
                        "which obscures all previous layers.")
                    baselayer = bands_comb
                else:

                    mask = Image.merge("L", (alpha,))
                    baselayer.paste(bands_comb, (0, 0), mask)

                    # Composite this image over the previous layer
                    #baselayer = Image.composite(baselayer, bands_comb, solid)


        # Attempt to write the image out to disk.
        self._write_to_file(baselayer)
        
        return 

    def _write_to_file(self, imageobj):
        """
        Writes the output image out to disk.

        * Raises NotImplementedError if you forgot to specify
          self.output_filename or self.image_format constants.

        * Raises OSError if there was a problem writing out the file.
        """
        if not self.output_filename:
            raise NotImplementedError, "You must specify an output filename"
        elif not self.image_format:
            raise NotImplementedError, "You must specify an output format"
        else:
            pass # Both values present, continue

        try:
            imageobj.save(os.path.join(self.output_path, self.output_filename),
                            self.image_format)
        except IOError, msg:
            raise

        return

