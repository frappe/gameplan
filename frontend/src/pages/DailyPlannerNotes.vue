<template>
  <div>
    <TextEditor
      v-if="$resources.note.data"
      class="mt-4"
      editor-class="pb-20 prose-sm"
      :content="$resources.note.data.content"
      placeholder="Use this space to plan your day, and jot down notes."
      @change="(val) => $resources.updateNote.submit(val)"
      :bubbleMenu="true"
      :extensions="[TaskExtension]"
    />
  </div>
</template>
<script>
import { TextEditor } from 'frappe-ui'
import TextEditorTaskExtension from '@/components/TextEditorTaskExtension'

export default {
  name: 'DailyPlannerNotes',
  props: ['date'],
  components: {
    TextEditor,
  },
  resources: {
    note() {
      return {
        method: 'gameplan.api.daily_note',
        params: {
          date: this.date,
        },
        auto: true,
        onError(e) {
          console.log(e)
          window.note_error = e
        },
      }
    },
    updateNote() {
      return {
        method: 'gameplan.api.update_daily_note',
        makeParams(content) {
          let date = this.$dayjs().format('YYYY-MM-DD')
          return {
            date,
            content,
          }
        },
        debounce: 500,
        onSuccess(note) {
          this.$resources.note.setData(note)
        },
      }
    },
  },
  computed: {
    TaskExtension() {
      return TextEditorTaskExtension
    },
  },
}
</script>
