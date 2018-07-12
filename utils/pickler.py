import pickle
class pickler:
    """ This class supports 'pickling' of a dictionary
    It takes a file name and an object.  If called to load an object that doesn't exist,
    an empty dictionary is returned
    """
    def __init__(self, filepath):
        self.filepath = filepath
        self.load()

    def clear(self):
        self.obj = {}
        self.save()

    def save(self):
        pickle.dump(self.obj, open(self.filepath,"wb"))

    def load(self):
        try:
            self.obj =  pickle.load(open(self.filepath, "rb"))
        except FileNotFoundError:
            self.obj = {}


