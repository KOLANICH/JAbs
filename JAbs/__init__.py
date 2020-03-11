__all__ = ("SelectedJVMInitializer", "ClassPathT", "ClassesImportSpecT")
import sys
from importlib import import_module

from .utils.pathListTools import ClassesImportSpecT, ClassPathT

implPkgNameMapping = {"cpython": "JPype", "graalpython": "GraalVM"}

implPkgName = implPkgNameMapping[sys.implementation.name]
pkg = import_module(".impls." + implPkgName, __package__)
SelectedJVMInitializer = pkg.SelectedJVMInitializer
