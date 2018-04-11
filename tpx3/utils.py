
# this should really be a class method of BitLogic, but to stay compatible with
# the current basil version, we add it at runtime
def toByteList(obj, bitwise = False):
    """
    Converts bitstring to a list of bytes
    If `bitwise` == True, we return a list of strings containing the binary repr
    of the bytes.
    """
    if obj.length() % 8 != 0:
        raise ValueError("""Cannot convert to array of bytes, if number of
        bits not a multiple of a byte""")
    nbytes = obj.length() / 8
    byteList = []

    # range from 0 to 40, reversed to get MSB first
    # for some reason list comprehension doesn't work here?
    for i in reversed(range(0, obj.length(), 8)):
        if bitwise == False:
            byteList += [obj[i+7:i].tovalue()]
        else:
            byteList += [obj[i+7:i].__str__()]

    return byteList
