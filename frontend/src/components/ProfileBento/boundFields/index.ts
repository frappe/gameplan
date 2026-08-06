import type { Component } from 'vue'
import ProfileBoundImageField from './ProfileBoundImageField.vue'
import ProfileBoundNameField from './ProfileBoundNameField.vue'
import ProfileBoundRichTextField from './ProfileBoundRichTextField.vue'
import ProfileBoundTextField from './ProfileBoundTextField.vue'
import type { ProfileBoundEditor } from '../types'

/**
 * Which control edits which kind of bound field.
 *
 * A table rather than a chain of `v-else-if` in the panel, so adding a sixth
 * bound field is a row in `profileBoundFields` and, at most, one entry here.
 * Every editor takes the same two props (`spec` and `draft`) and stages its edit
 * on the draft, which is what lets them be swapped by name.
 */
export const profileBoundFieldEditors: Record<ProfileBoundEditor, Component> = {
  name: ProfileBoundNameField,
  text: ProfileBoundTextField,
  richText: ProfileBoundRichTextField,
  image: ProfileBoundImageField,
}
