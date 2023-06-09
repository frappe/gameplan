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
      class="absolute right-0 top-0 flex space-x-2"
      :class="{ 'mr-4 mt-4': border || editReadme }"
      v-if="editable"
    >
      <Tooltip v-if="!editReadme && !$readOnlyMode" text="Edit">
        <Button variant="ghost" label="Edit" @click="editReadmeAndFocus">
          <template #icon><LucideEdit2 class="w-4" /> </template>
        </Button>
      </Tooltip>
      <template v-if="editReadme">
        <Button
          @click="
            () => {
              editReadme = false
              resource.setValue.submit({ [fieldname]: resource.doc[fieldname] })
            }
          "
        >
          <template #prefix><LucideSave class="w-4" /></template>
          Save
        </Button>
        <Button
          @click="
            () => {
              editReadme = false
              resource.reload()
            }
          "
        >
          <template #prefix><LucideRotateCcw class="w-4" /></template>
          Discard
        </Button>
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
