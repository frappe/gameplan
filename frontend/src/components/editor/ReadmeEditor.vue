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
      <Tooltip v-if="!editReadme && !$readOnlyMode" text="Edit">
        <Button variant="ghost" label="Edit" icon="lucide-edit-2" @click="editReadmeAndFocus" />
      </Tooltip>
      <template v-if="editReadme">
        <Button icon-left="lucide-save" :loading="saving" @click="saveReadme">Save</Button>
        <Button icon-left="lucide-rotate-ccw" :disabled="saving" @click="discardReadme">
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
    // Editing state, so a parent can open the editor straight away and react to
    // it (the profile card grows itself while its About editor is open).
    editing: {
      type: Boolean,
      default: false,
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
  emits: ['update:editing'],
  data() {
    return {
      expand: false,
      saving: false,
      extensions: richTextExtensions(),
      gameplanToolbar,
      gameplanFloatingToolbar,
    }
  },
  computed: {
    editReadme: {
      get() {
        return this.editing
      },
      set(value) {
        this.$emit('update:editing', value)
      },
    },
  },
  mounted() {
    if (this.editReadme) this.focusEditor()
  },
  setup() {
    const readme = ref(null)
    const readmeElement = ref(null)
    const { height } = useElementSize(readmeElement)

    return {
      readme,
      readmeElement,
      readmeHeight: height,
    }
  },
  methods: {
    editReadmeAndFocus() {
      this.editReadme = true
      this.expand = true
      this.focusEditor()
    },
    focusEditor() {
      this.$nextTick(() => {
        this.$refs.readme?.editor?.commands.focus()
      })
    },
    async saveReadme() {
      if (this.saving) return

      this.saving = true
      try {
        await this.resource.setValue.submit({ [this.fieldname]: this.resource.doc[this.fieldname] })
        this.editReadme = false
      } catch (error) {
        // Stay open so the draft is not lost. Whoever owns the resource reports
        // the failure; closing here would hide it behind stale content.
      } finally {
        this.saving = false
      }
    },
    discardReadme() {
      this.editReadme = false
      this.resource.reload()
    },
  },
}
</script>
