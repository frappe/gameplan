# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals

import io

from frappe.core.doctype.file.file import File


def remove_background(file: File):
	from PIL import Image
	from rembg import remove

	input_image = Image.open(file.get_full_path())
	output_image = remove(input_image)
	output = io.BytesIO()
	output_image.save(output, "png")
	return output.getvalue()
