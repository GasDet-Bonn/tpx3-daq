
# this should really be a class method of BitLogic, but to stay compatible with 
# the current basil version, we add it at runtime
def toByteList(self):
    """
    Converts bitstring to a list of bytes
    """
    if self.length() % 8 != 0:
        raise ValueError("""Cannot convert to array of bytes, if number of 
        bits not a multiple of a byte""")
    nbytes = self.length() / 8
    byteList = []

    # range from 0 to 40, reversed to get MSB first
    # for some reason list comprehension doesn't work here?
    for i in reversed(range(0, self.length(), 8)):
        byteList += [self[i+7:i].tovalue()]

    return byteList
