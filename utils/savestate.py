import json
class savestate:
    """ This class supports the serialization of a dictionary
    It takes a file name and an object.  If called to load an object that doesn't exist,
    an empty dictionary is returned
    """
    def __init__(self, filepath):
        self.filepath = filepath
        self.load()

    def clear(self):
        self.obj = {}
        self.save()

    def pop(self,key):
        self.obj.delete(key)

    def load(self):
        try:
            self.obj =  json.load(open(self.filepath, "r"))
        except FileNotFoundError:
            self.obj = {}

    def save(self):
        json.dump(self.obj, open(self.filepath,"w"))


