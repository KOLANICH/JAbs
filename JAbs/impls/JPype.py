import typing
import warnings
from pathlib import Path

import _jpype
import jpype
import jpype.beans

from ..JVMInitializer import JVMInitializer
from ..utils.pathListTools import ClassesImportSpecT, ClassPathT, appendPathsList, getTupleFromPathProperty, pathsList2String

ji = None


class RootClassLoaderWrapper:
	__slots__ = ("cl", "children")

	def __init__(self, cl):
		self.cl = cl
		self.children = {}

	def free(self):
		del self.cl


class ClassLoaderWrapper(RootClassLoaderWrapper):
	__slots__ = ("cl", "children", "parent")

	def __init__(self, cl, parent):
		super().__init__(cl)
		self.parent = parent
		parent.children[id(cl)] = self

	def free(self):
		if self.children:
			raise ValueError("Cannot free a loader with children")

		del self.parent[id(self.cl)]
		super().free()


class _JPypeInitializer(JVMInitializer):
	__slots__ = ("_allowShutdown", "_libPaths")
	classPathPropertyName = "java.class.path"

	_defaultLibsPaths = None

	def __init__(self, classPaths: ClassPathT, classes2import: ClassesImportSpecT, *, libPaths=None, _allowShutdown: bool = False) -> None:
		self._allowShutdown = _allowShutdown
		self._libPaths = libPaths
		if _allowShutdown:
			warnings.warn("`_allowShutdown` was used to allow `jpype.shutdownJVM`. See https://jpype.readthedocs.io/en/latest/userguide.html#unloading-the-jvm and https://github.com/jpype-project/jpype/blob/master/native/common/jp_context.cpp#L290")

		# these ones are defered. Before JVM is initialized they are accumulated by JPipe itself. They are not the same as loaded in runtime. Ones loaded in runtime may have various conflicts because of different classloaders.
		for cp in classPaths:
			jpype._classpath.addClassPath(cp.absolute())

		# because JPype accumulates them itself, we put here nothing
		super().__init__([], classes2import)

	def selectJVM(self) -> Path:
		return Path(jpype.getDefaultJVMPath())

	@property
	def classPath(self, classPath: ClassPathT) -> None:
		return super().classPath

	@classPath.setter
	def classPath(self, classPath: ClassPathT) -> None:
		raise NotImplementedError("For this backend redefining classpath is not supported, use `appendClassPath`")

	def appendClassPath(self, classPaths: ClassPathT) -> None:
		for cp in classPaths:
			jpype._classpath.addClassPath(cp.absolute())

	def appendLibPath(self, libPaths: ClassPathT) -> None:
		raise NotImplementedError("Unavailable in JPype. Restart the JVM.")

	def loadClass(self, name: str):
		res = jpype.JClass(name)

		assert isinstance(res, jpype._jpype._JClass), "Class `" + repr(name) + "` is not loaded (res.__class__ == " + repr(res.__class__) + "), it's JPype drawback that when something is missing it returns a `jpype._jpackage.JPackage`, that errors only when one tries to instantiate it as a class"  # pylint: disable=c-extension-no-member,protected-access
		return res

	def reflClass2Class(self, cls) -> typing.Any:  # pylint: disable=no-self-use
		return jpype.types.JClass(cls)

	def prepareJVM(self) -> None:
		if jpype.isJVMStarted():
			warnings.warn("JPype disallows starting multiple JVMs or restarting it. Assuming that JVM is already started with needed arguments, such as classpath.")
			if not self._allowShutdown:
				return
			jpype.shutdownJVM()

		# WARNING
		# 1. sys.class.path doesn't work
		# 2. only classpath set via "-Djava.class.path=" takes effect, https://github.com/jpype-project/jpype/issues/177
		# 3. only libpath set at start up via "-Djava.library.path=" takes effect
		args = [jpype.getDefaultJVMPath(), "-ea"]
		if self._libPaths:
			if self.__class__._defaultLibsPaths is None:
				from ..utils.javaPropsInASeparateProcess import getDefaultJavaPropsFromSubprocess

				defaultProps = getDefaultJavaPropsFromSubprocess(self)
				self.__class__._defaultLibsPaths = getTupleFromPathProperty(defaultProps.get(self.__class__.libPathPropertyName, ""))

			libPaths = appendPathsList(self.__class__._defaultLibsPaths, self._libPaths)
			args.append("-D" + self.__class__.libPathPropertyName + "=" + pathsList2String(libPaths))

		jpype.startJVM(*args, convertStrings=False, ignoreUnrecognized=False)

	def reflectClass(self, cls) -> typing.Any:
		return cls.class_

	@staticmethod
	def _Implements(className: str, parents: typing.Tuple[typing.Type, ...], attrs: typing.Dict[str, typing.Any]):
		interface = parents[0]
		res = type(className, (), attrs)
		dec = jpype.JImplements(interface)
		return dec(res)

	_Override = staticmethod(jpype.JOverride)


class JPypeInitializer(_JPypeInitializer):
	__slots__ = ()

	def __new__(cls, classPaths: ClassPathT, classes2import: ClassesImportSpecT, *args, **kwargs):
		global ji
		if ji is None:
			ji = _JPypeInitializer(classPaths, classes2import, *args, **kwargs)
		else:
			ji.appendClassPath(classPaths)
			ji.loadClasses(classes2import)

		return ji


SelectedJVMInitializer = JPypeInitializer
