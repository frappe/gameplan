<template>
  <div class="relative px-4 py-4 border rounded-xl">
    <div class="absolute top-0 right-0 z-10 flex mt-4 mr-4 space-x-2">
      <Button
        v-if="!editReadme"
        label="Edit"
        iconLeft="edit-2"
        @click="editReadmeAndFocus"
      />
      <template v-else>
        <Button
          label="Save"
          iconLeft="save"
          @click="
            () => {
              editReadme = false
              project.setValue.submit({ readme: project.doc.readme })
            }
          "
        />
        <Button
          label="Cancel"
          iconLeft="rotate-ccw"
          @click="
            () => {
              editReadme = false
              project.reload()
            }
          "
        />
      </template>
    </div>
    <TextEditor
      ref="readme"
      editor-class="pb-20"
      :content="project.doc.readme"
      placeholder="Use this space to write a detailed description of your project"
      @change="(val) => (project.doc.readme = val)"
      :bubbleMenu="true"
      :floating-menu="true"
      :editable="editReadme"
    />
  </div>
</template>
<script>
import { TextEditor } from 'frappe-ui'
export default {
  name: 'ProjectDetailOverviewReadme',
  props: ['project'],
  components: { TextEditor },
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
