import typing
from collections import OrderedDict
from os import pathsep as PATH_sep
from pathlib import Path

__all__ = ("ClassesImportSpecT", "ClassPathT", "dedupPreservingOrder", "normalizePathsList", "appendPathsList", "pathsList2String", "getTupleFromPathProperty")

ClassesImportSpecT = typing.Union[typing.Iterable[str], typing.Mapping[str, str]]
ClassPathT = typing.Iterable[typing.Union[Path, str]]


def dedupPreservingOrder(*args: typing.Iterable[ClassPathT]) -> ClassPathT:
	dedup = OrderedDict()
	for col in args:
		if col:
			for el in col:
				dedup[el] = True

	return dedup.keys()


def normalizePathsList(classPaths: ClassPathT) -> ClassPathT:
	for f in classPaths:
		if isinstance(f, Path):
			f = str(f.absolute())
		yield f


def appendPathsList(classPaths: ClassPathT, origClassPath: typing.Iterable[str] = ()):
	classPaths = list(classPaths)
	res = dedupPreservingOrder(list(normalizePathsList(classPaths)), origClassPath)
	return res


def pathsList2String(classPaths):
	return PATH_sep.join(normalizePathsList(classPaths))


def getTupleFromPathProperty(propString):
	cps = propString.split(PATH_sep)

	res = [None] * len(cps)
	for i, p in enumerate(cps):
		try:
			res[i] = Path(p)
		except BaseException:
			res[i] = p
	return tuple(res)
