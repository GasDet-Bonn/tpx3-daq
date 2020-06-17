import sys

class utils():
	def print_nice(f):
		if isinstance(f, int):
			return str(f)
		elif isinstance(f, float):
			if abs(f - round(f)) <= sys.float_info.epsilon:
				return str(round(f))
			else:
				return str(f)
		else:
			raise TypeError("`print_nice` only supports floats and ints! Input " +
							"is of type {}!".format(type(f)))
