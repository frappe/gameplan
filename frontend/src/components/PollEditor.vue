<template>
  <div class="space-y-4">
    <Input
      type="text"
      label="Question"
      v-model="poll.title"
      @change="$emit('update:poll', poll)"
    />
    <Input
      type="checkbox"
      label="Anonymous"
      v-model="poll.anonymous"
      @change="$emit('update:poll', poll)"
    />
    <div class="space-y-2">
      <div class="text-sm leading-4 text-gray-700">Options</div>
      <Input
        v-for="option in poll.options"
        :key="option.idx"
        :placeholder="`Option ${option.idx}`"
        :value="option.title"
        @input="onOptionChange(option, $event)"
      />
    </div>
    <div class="flex justify-end space-x-2">
      <Button v-bind="discardButtonProps">Discard</Button>
      <Button v-bind="submitButtonProps" appearance="primary"> Submit </Button>
    </div>
  </div>
</template>
<script>
import { debounce } from 'frappe-ui'

export default {
  name: 'PollEditor',
  props: ['poll', 'submitButtonProps', 'discardButtonProps'],
  events: ['update:poll'],
  methods: {
    onOptionChange: debounce(function (option, value) {
      option.title = value

      let lastOption =
        this.poll.options.length > 0 &&
        this.poll.options[this.poll.options.length - 1]

      if (lastOption?.title) {
        this.poll.options.push({
          title: '',
          idx: lastOption.idx + 1,
        })
      }
      this.$emit('update:poll', this.poll)
    }, 100),
  },
}
</script>
