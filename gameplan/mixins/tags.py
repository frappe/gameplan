import frappe
from bs4 import BeautifulSoup


class HasTags:
	def update_tags(self):
		"""
		Updates the document's child table 'tags' based on span.tag-item elements in an HTML field.
		The HTML field is determined by `getattr(self, 'tags_content_field', 'content')`.
		Assumes self.tags is a child table field with columns 'tag' (Link to Tag DocType storing its ID/name)
		and 'label' (Data storing tag_name).
		Creates master tags if they don't exist.
		Populates self.newly_created_master_tags with labels of master tags created during this update.
		Updates the HTML content with data-tag-id attributes for new/existing tags.
		"""
		content_field_name = getattr(self, "tags_content_field", "content")

		if not hasattr(self, content_field_name):
			self.newly_created_master_tags = []
			return

		html_content = getattr(self, content_field_name)

		if self.tags is None:
			self.tags = []

		self.newly_created_master_tags = []

		if not html_content:
			if self.tags:
				self.tags = []
			return

		target_master_tag_ids, new_html_content = self._get_tag_ids_from_html(html_content)

		if new_html_content != html_content:
			setattr(self, content_field_name, new_html_content)

		self._sync_child_table_tags(target_master_tag_ids)

	def _ensure_tag_doc(self, tag_label: str) -> tuple[str | None, bool]:
		"""
		Ensures a GP Tag document with the given label exists. Creates if necessary.
		Returns (tag_doc_name, was_newly_created).
		"""
		if not tag_label:
			return None, False

		existing_tag_id = frappe.db.get_value("GP Tag", {"label": tag_label}, "name")

		if existing_tag_id:
			return existing_tag_id, False

		try:
			new_tag_doc = frappe.new_doc("GP Tag", label=tag_label)
			new_tag_doc.insert(ignore_permissions=True)
			return new_tag_doc.name, True
		except Exception as e:
			# Log error, e.g., if a unique constraint on label is violated by a concurrent process.
			frappe.log_error(
				f"Failed to create GP Tag with label: {tag_label}. Error: {str(e)}", title="HasTags Mixin"
			)
			# Defensive check: the tag might have been created by a concurrent process.
			existing_tag_id_after_fail = frappe.db.get_value("GP Tag", {"label": tag_label}, "name")
			if existing_tag_id_after_fail:
				return existing_tag_id_after_fail, False
			return None, False

	def _get_tag_ids_from_html(self, html_content: str) -> tuple[list[str], str]:
		"""
		Parses HTML, extracts tag labels, ensures master GP Tag documents exist,
		updates data-tag-id attributes in the HTML, populates self.newly_created_master_tags,
		and returns unique master GP Tag IDs and the modified HTML content.
		"""
		soup = BeautifulSoup(html_content, "html.parser")
		content_tag_elements = soup.find_all("span", class_="tag-item")

		processed_master_tag_ids = set()
		html_was_modified = False

		for tag_el in content_tag_elements:
			tag_label_from_content = tag_el.get("data-tag-label")
			if tag_label_from_content:
				tag_label_from_content = tag_label_from_content.strip()
				if not tag_label_from_content:
					continue

				master_tag_id, was_newly_created = self._ensure_tag_doc(tag_label_from_content)

				if master_tag_id:
					processed_master_tag_ids.add(master_tag_id)
					if was_newly_created:
						self.newly_created_master_tags.append(tag_label_from_content)

					# Update data-tag-id attribute in the HTML element
					if tag_el.get("data-tag-id") != master_tag_id:
						tag_el["data-tag-id"] = master_tag_id
						html_was_modified = True
				else:
					frappe.log_error(
						f"Could not ensure master tag for label: {tag_label_from_content} from content.",
						title="HasTags Mixin",
					)

		final_html_content = str(soup) if html_was_modified else html_content
		return list(processed_master_tag_ids), final_html_content

	def _sync_child_table_tags(self, target_tag_ids: list[str]):
		"""
		Synchronizes the self.tags child table with the target list of master GP Tag IDs.
		"""
		current_tag_ids = [d.tag for d in self.tags if d.tag]

		tags_to_add = list(set(target_tag_ids) - set(current_tag_ids))
		tags_to_remove = list(set(current_tag_ids) - set(target_tag_ids))

		if tags_to_remove:
			self.tags = [row for row in self.tags if row.tag not in tags_to_remove]

		if tags_to_add:
			for tag_id_to_add in tags_to_add:
				master_label = frappe.db.get_value("GP Tag", tag_id_to_add, "label")

				if not master_label:
					# This might happen if _ensure_tag_doc failed or the ID is invalid.
					frappe.log_error(
						f"Cannot find master label for GP Tag ID: {tag_id_to_add}."
						" Skipping adding to child table.",
						title="HasTags Mixin",
					)
					continue

				self.append("tags", {"tag": tag_id_to_add, "label": master_label})
