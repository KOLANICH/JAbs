import typing
from abc import ABC, abstractmethod
from pathlib import Path

from .utils.pathListTools import ClassesImportSpecT, ClassPathT, appendPathsList, dedupPreservingOrder, getTupleFromPathProperty, pathsList2String


class JVMInitializer(ABC):
	#__slots__ = ("sys", )  # we inject loaded classes right into this class

	classPathPropertyName = "sys.class.path"
	classPathPropertyName = "java.class.path"  # new
	libPathPropertyName = "java.library.path"

	def __init__(self, classPaths: ClassPathT, classes2import: ClassesImportSpecT, *, libPaths=None) -> None:
		self.prepareJVM()
		self.sys = self.loadClass("java.lang.System")
		classPaths = list(classPaths)
		self.appendClassPath(classPaths)
		self.loadClasses(classes2import)

	class _Implements(type):
		"""Used as a metaclass to wrap python classes implementing interfaces defined in JVM code"""

		__slots__ = ()

	def _Override(self, meth: typing.Callable) -> typing.Callable:
		"""Used as a decorator to wrap python methods overriding methods defined in JVM code"""
		return meth

	@abstractmethod
	def selectJVM(self) -> Path:
		"""Returns Path to libjvm.so"""
		raise NotImplementedError()

	@abstractmethod
	def prepareJVM(self):
		"""Starts JVM and sets its settings"""
		raise NotImplementedError()

	def reflClass2Class(self, cls) -> typing.Any:  # pylint: disable=no-self-use
		"""Transforms a reflection object for a class into an object usable by python"""
		return cls

	def reflectClass(self, cls) -> typing.Any:
		"""Transforms a a class into a reflection object for a class"""
		raise NotImplementedError

	@abstractmethod
	def loadClass(self, name: str) -> typing.Any:
		"""Returns a class"""
		raise NotImplementedError()

	def getSysPropsDict(self):
		return {str(k): str(self.sys.getProperty(k)) for k in self.sys.getProperties()}

	@property
	def libPathStr(self) -> str:
		"""libpath string"""
		return str(self.sys.getProperty(self.__class__.libPathPropertyName))

	@libPathStr.setter
	def libPathStr(self, classPath: str) -> None:
		self.sys.setProperty(self.__class__.libPathPropertyName, classPath)

	@property
	def classPathStr(self) -> str:
		"""classpath string"""
		return str(self.sys.getProperty(self.__class__.classPathPropertyName))

	@classPathStr.setter
	def classPathStr(self, classPath: str) -> None:
		self.sys.setProperty(self.__class__.classPathPropertyName, classPath)

	@property
	def classPath(self) -> typing.Iterable[str]:
		"""classpath string separated into paths"""
		return getTupleFromPathProperty(self.classPathStr)

	@classPath.setter
	def classPath(self, classPaths: ClassPathT) -> None:
		self.classPathStr = pathsList2String(classPaths)

	def appendClassPath(self, classPaths: ClassPathT) -> None:
		"""Adds a jar into classpath"""
		self.classPath = appendPathsList(classPaths, self.classPath)

	@property
	def libPath(self) -> typing.Iterable[str]:
		"""classpath string separated into paths"""
		return getTupleFromPathProperty(self.libPathStr)

	@libPath.setter
	def libPath(self, libPaths: ClassPathT) -> None:
		self.libPathStr = pathsList2String(libPaths)

	def appendLibPath(self, libPaths: ClassPathT) -> None:
		"""Adds a lib into libpath"""
		self.libPath = appendPathsList(libPaths, self.libPath)

	def loadClasses(self, classes2import: ClassesImportSpecT) -> None:
		"""Loads the classes that are required to be loaded and injects them into `self`, using the last component of a path as a property"""
		if isinstance(classes2import, (list, tuple)):
			newSpec = {}
			for el in classes2import:
				if isinstance(el, tuple):
					name = el[1]
					path = el[0]
				else:
					name = el.split(".")[-1]
					path = el

				newSpec[name] = path

			classes2import = newSpec

			for k, className in newSpec.items():
				setattr(self, k, self.loadClass(className))
		else:
			raise ValueError("`classes2import` have wrong type", classes2import)
