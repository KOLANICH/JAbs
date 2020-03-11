import sys

# pylint:disable=import-outside-toplevel

try:
	import cbor2 as serializer
except ImportError:
	try:
		import ujson as serializer
	except ImportError:
		import json as serializer

__doc__ = "This module starts a brand new JVM in a separate process in order to get the props (that can be unchangeable after JVM is started) prior starting the JVM in the main process. The params are passed via JSON into stdin."


def _getJavaPropsInASeparateProcessExecutor():
	"""Since we cannot shutdown a VM, we start a separate process to get the stuff"""
	backendName = sys.stdin.readline()
	if backendName[-1] == "\n":
		backendName = backendName[:-1]
		if backendName[-1] == "\r":
			backendName = backendName[:-1]
	if not backendName.isalnum():
		raise ValueError("Must be a name of a module under .impls")

	from importlib import import_module

	pkg = import_module("..impls." + backendName, __package__)
	SelectedJVMInitializer = pkg.SelectedJVMInitializer

	ji = SelectedJVMInitializer([], [])
	res = ji.getSysPropsDict()
	res = serializer.dumps(res)
	if isinstance(res, str):
		res = res.encode("utf-8")
	sys.stdout.buffer.write(res)


_defaultProps = None


def getDefaultJavaPropsFromSubprocess(backend):
	import subprocess

	if not isinstance(backend, str):
		if not isinstance(backend, type):
			backend = backend.__class__

		backendName = backend.__module__.split(".")[-1]
	else:
		backendName = backend
	assert backendName.isalnum()
	args = [sys.executable, "-m", __name__]

	with subprocess.Popen(args, stdout=subprocess.PIPE, stdin=subprocess.PIPE, shell=False) as p:
		p.stdin.write(backendName.encode("utf-8"))
		p.stdin.flush()
		p.stdin.close()
		p.wait()
		res = p.stdout.read()

	return serializer.loads(res)


if __name__ == "__main__":
	_getJavaPropsInASeparateProcessExecutor()
