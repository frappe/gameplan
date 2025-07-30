# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import io

from frappe.core.doctype.file.file import File


def remove_background(file: File):
	try:
		from PIL import Image
		from rembg import remove
	except ImportError as exc:
		raise ImportError(
			"rembg package is required for background removal. Please install it with: pip install rembg"
		) from exc

	input_image = Image.open(file.get_full_path())
	output_image = remove(input_image)
	output = io.BytesIO()
	output_image.save(output, "png")
	return output.getvalue()


def is_rembg_available():
	"""Check if rembg package is available"""
	try:
		import importlib.util

		return importlib.util.find_spec("rembg") is not None
	except ImportError:
		return False
