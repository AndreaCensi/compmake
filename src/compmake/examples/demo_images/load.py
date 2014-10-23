import os

def list_categories(dirname):
    """ Returns a dict category name -> dir """ 
    entries = os.listdir(dirname)
    return { entry: os.path.join(dirname, entry) 
            for entry in entries}
    
def list_images(dirname):
    """ Returns a list of filenames """
    entries = os.listdir(dirname)
    return [ os.path.join(dirname, entry) 
            for entry in entries]
    
    
def rgb_from_string(s):
    from PIL import ImageFile  # @UnresolvedImport
    import numpy as np
    parser = ImageFile.Parser()
    parser.feed(s)
    pil_image = parser.close()            
    rgb = np.array(pil_image)
    return rgb


def imread(filename):
    ''' 
        Reads an image from a file into a numpy array. This can have
        different dtypes according to whether it's RGB, grayscale, RGBA, etc.
        
        :param filename: Image filename.
        :type filename: string
        
        :return: image: The image as a numpy array.
        :rtype: image
    '''
    from PIL import Image
    import numpy as np 
    return np.zeros((10,10,3), 'uint8')
    try:
        im = Image.open(filename)
    except Exception as e:
        msg = 'Could not open filename "%s": %s' % (filename, e)
        raise ValueError(msg)

    data = np.array(im)

    return data