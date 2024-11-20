<template>
  <div
    class="relative"
    :class="{
      'rounded-lg border px-3 py-3': border || editReadme,
      'max-h-[150px] overflow-hidden': !expand && collapsible,
    }"
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
      :class="{ 'mr-3 mt-3': border || editReadme }"
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
    <div
      class="absolute bottom-0 right-0 flex"
      :class="{ 'p-3': border || editReadme }"
      v-if="collapsible && readmeHeight > 150"
    >
      <Tooltip text="Expand/Collapse">
        <!-- TODO: Tooltip bug, button click fires twice -->
        <div>
          <Button variant="ghost" @click="expand = !expand">
            <template #icon>
              <LucideUnfoldVertical class="w-4" />
            </template>
          </Button>
        </div>
      </Tooltip>
    </div>
  </div>
</template>
<script>
import { ref } from 'vue'
import { Tooltip } from 'frappe-ui'
import { useElementSize } from '@vueuse/core'
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
    collapsible: {
      type: Boolean,
      default: false,
    },
  },
  components: { TextEditor, Tooltip },
  data() {
    return {
      editReadme: false,
      expand: false,
    }
  },
  setup() {
    const readme = ref(null)
    const { height } = useElementSize(readme)

    return {
      readme,
      readmeHeight: height,
    }
  },
  methods: {
    editReadmeAndFocus() {
      this.editReadme = true
      this.expand = true
      this.$nextTick(() => {
        this.$refs.readme.editor.commands.focus()
      })
    },
  },
}
</script>
