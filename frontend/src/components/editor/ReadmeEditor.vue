<template>
  <div
    class="relative"
    :class="{
      'max-h-[150px] overflow-hidden': !expand && collapsible,
    }"
  >
    <div ref="readmeElement">
      <GPEditor
        ref="readme"
        :extensions="extensions"
        editor-class="prose-v3"
        :content="resource.doc[fieldname]"
        :placeholder="placeholder"
        @change="(val) => (resource.doc[fieldname] = val)"
        :bubble-menu="gameplanToolbar"
        :floating-menu="gameplanFloatingToolbar"
        :editable="editReadme"
      />
    </div>
    <div
      class="absolute right-0 top-0 flex space-x-2"
      :class="{ 'mr-3 mt-3': border || editReadme }"
      v-if="editable"
    >
      <Tooltip v-if="!editReadme && !readOnlyMode" text="Edit">
        <Button variant="ghost" label="Edit" icon="lucide-edit-2" @click="editReadmeAndFocus" />
      </Tooltip>
      <template v-if="editReadme">
        <Button
          icon-left="lucide-save"
          @click="
            () => {
              editReadme = false
              resource.setValue.submit({ [fieldname]: resource.doc[fieldname] })
            }
          "
        >
          Save
        </Button>
        <Button
          icon-left="lucide-rotate-ccw"
          @click="
            () => {
              editReadme = false
              resource.reload()
            }
          "
        >
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
          <Button variant="ghost" icon="lucide-unfold-vertical" @click="expand = !expand" />
        </div>
      </Tooltip>
    </div>
  </div>
</template>
<script>
import { ref } from 'vue'
import { Tooltip } from 'frappe-ui'
import { useElementSize } from '@vueuse/core'
import GPEditor from '@/components/editor/GPEditor.vue'
import { gameplanToolbar, gameplanFloatingToolbar } from '@/components/editor/toolbars'
import { richTextExtensions } from '@/components/editor/richTextExtensions'

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
  components: { GPEditor, Tooltip },
  data() {
    return {
      editReadme: false,
      expand: false,
      extensions: richTextExtensions(),
      gameplanToolbar,
      gameplanFloatingToolbar,
    }
  },
  setup() {
    const readme = ref(null)
    const readmeElement = ref(null)
    const { height } = useElementSize(readmeElement)

    return {
      readme,
      readmeElement,
      readmeHeight: height,
      readOnlyMode: Boolean(window.read_only_mode),
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
