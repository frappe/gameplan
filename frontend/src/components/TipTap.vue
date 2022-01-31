<template>
  <div v-if="editor">
    <BubbleMenu
      class="bubble-menu"
      :tippy-options="{ duration: 100 }"
      :editor="editor"
    >
      <button
        v-for="(button, i) in bubbleMenuButtons"
        :key="button.label"
        type="button"
        class="relative inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 focus:z-10 focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
        :class="{
          'bg-gray-200': button.isActive(),
          '-ml-px': i > 0,
          'rounded-l-md': i === 0,
          'rounded-r-md': i === bubbleMenuButtons.length - 1,
        }"
        @click="button.action"
      >
        {{ button.label }}
      </button>
    </BubbleMenu>
    <FloatingMenu
      class="space-x-2 floating-menu"
      :tippy-options="{ duration: 100 }"
      :editor="editor"
    >
      <button
        type="button"
        class="inline-flex items-center px-2.5 py-1 border border-transparent text-xs font-medium rounded text-gray-700 bg-gray-100 focus:outline-none focus:ring-1 focus:ring-offset-2 focus:ring-indigo-500"
        v-for="button in floatingMenuButtons"
        @click="button.action"
        :class="button.isActive() ? 'bg-gray-300' : 'hover:bg-gray-200'"
      >
        {{ button.label }}
      </button>
    </FloatingMenu>
    <editor-content :editor="editor" class="prose-sm prose" />
  </div>
</template>

<script>
import { Editor, EditorContent, BubbleMenu, FloatingMenu } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'

export default {
  components: {
    EditorContent,
    BubbleMenu,
    FloatingMenu,
  },
  props: ['content'],
  emits: ['update'],
  expose: ['editor'],
  data() {
    return {
      editor: null,
    }
  },
  watch: {
    content(newValue, oldValue) {
      // console.log(newValue, oldValue)
      // if (newValue !== oldValue) {
      //   this.editor.commands.setContent(newValue || '<p><br></p>')
      // }
    },
  },
  mounted() {
    this.editor = new Editor({
      content: this.content || '<p></p>',
      editorProps: {
        attributes: {
          class: 'prose prose-sm prose-p:my-1',
        },
      },
      extensions: [StarterKit],
      onUpdate: ({ editor }) => {
        this.$emit('update', editor.getHTML())
      },
    })
  },
  beforeUnmount() {
    this.editor.destroy()
  },
  computed: {
    bubbleMenuButtons() {
      return [
        {
          label: 'Bold',
          action: () => this.editor.chain().focus().toggleBold().run(),
          isActive: () => this.editor.isActive('bold'),
        },
        {
          label: 'Italic',
          action: () => this.editor.chain().focus().toggleItalic().run(),
          isActive: () => this.editor.isActive('italic'),
        },
        {
          label: 'Strike',
          action: () => this.editor.chain().focus().toggleStrike().run(),
          isActive: () => this.editor.isActive('strike'),
        },
      ]
    },
    floatingMenuButtons() {
      return [
        {
          label: 'H2',
          action: () =>
            this.editor.chain().focus().toggleHeading({ level: 2 }).run(),
          isActive: () => this.editor.isActive('heading', { level: 2 }),
        },
        {
          label: 'H3',
          action: () =>
            this.editor.chain().focus().toggleHeading({ level: 3 }).run(),
          isActive: () => this.editor.isActive('heading', { level: 3 }),
        },
        {
          label: 'Bullet List',
          action: () => this.editor.chain().focus().toggleBulletList().run(),
          isActive: () => this.editor.isActive('bulletList'),
        },
      ]
    },
  },
}
</script>
