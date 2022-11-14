<template>
  <div
    class="relative rounded-xl"
    :class="{ 'border px-4 py-4': border || editReadme }"
  >
    <TextEditor
      ref="readme"
      editor-class="prose-sm"
      :content="resource.doc[fieldname]"
      :placeholder="placeholder"
      @change="(val) => (resource.doc[fieldname] = val)"
      :bubbleMenu="true"
      :floating-menu="true"
      :editable="editReadme"
    />
    <div
      class="absolute top-0 right-0 flex space-x-2"
      :class="{ 'mt-4 mr-4': border || editReadme }"
      v-if="editable"
    >
      <Tooltip v-if="!editReadme && !$readOnlyMode" text="Edit">
        <Button
          icon="edit-2"
          label="Edit"
          @click="editReadmeAndFocus"
          appearance="minimal"
        />
      </Tooltip>
      <template v-if="editReadme">
        <Button
          label="Save"
          iconLeft="save"
          @click="
            () => {
              editReadme = false
              resource.setValue.submit({ [fieldname]: resource.doc[fieldname] })
            }
          "
        />
        <Button
          label="Discard"
          iconLeft="rotate-ccw"
          @click="
            () => {
              editReadme = false
              resource.reload()
            }
          "
        />
      </template>
    </div>
  </div>
</template>
<script>
import { Tooltip } from 'frappe-ui'
import TextEditor from '@/components/TextEditor.vue'
export default {
  name: 'ReadmeEditor',
  props: {
    resource: {
      type: Object,
      required: true,
    },
    fieldname: {
      type: String,
      required: true,
    },
    editable: {
      type: Boolean,
      default: true,
    },
    placeholder: {
      type: String,
    },
    border: {
      type: Boolean,
      default: true,
    },
  },
  components: { TextEditor, Tooltip },
  data() {
    return {
      editReadme: false,
    }
  },
  methods: {
    editReadmeAndFocus() {
      this.editReadme = true
      this.$nextTick(() => {
        this.$refs.readme.editor.commands.focus()
      })
    },
  },
}
</script>
