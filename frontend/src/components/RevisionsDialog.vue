<template>
  <Dialog :options="{ title, size: '3xl' }" v-model="showDialog">
    <template #body-content>
      <div class="mb-2 flex items-center text-base" v-if="currentRevision">
        <UserInfo :email="currentRevision.owner" v-slot="{ user }">
          <UserProfileLink class="mr-3" :user="user.name">
            <UserAvatar :user="user.name" />
          </UserProfileLink>
          <div>
            <UserProfileLink
              class="font-medium text-ink-gray-8 hover:text-ink-blue-4"
              :user="user.name"
            >
              {{ user.full_name }}
            </UserProfileLink>
            <time
              class="block text-ink-gray-5"
              :datetime="currentRevision.creation"
              :title="dayjsLocal(currentRevision.creation)"
            >
              {{ dayjsLocal(currentRevision.creation).format('LLL') }}
            </time>
          </div>
        </UserInfo>
      </div>
      <div
        v-if="currentRevision"
        v-html="htmlDiff"
        class="ProseMirror prose prose-sm rounded-md prose-p:my-1 prose-table:table-fixed prose-th:relative prose-th:border prose-th:border-outline-gray-2 prose-th:bg-surface-gray-2 prose-th:p-2 prose-td:relative prose-td:border prose-td:border-outline-gray-2 prose-td:p-2"
      />
    </template>
    <template v-if="currentRevision && (hasNext || hasPrevious)" #actions>
      <div class="flex w-full justify-between">
        <div>
          <Button @click="previous" v-if="hasPrevious"> Previous </Button>
        </div>
        <Button @click="next" v-if="hasNext">Next</Button>
      </div>
    </template>
  </Dialog>
</template>
<script>
import { dayjsLocal } from 'frappe-ui'
import HtmlDiff from 'htmldiff-js'
import UserProfileLink from './UserProfileLink.vue'

export default {
  name: 'RevisionsDialog',
  props: {
    modelValue: {
      type: Boolean,
      default: false,
    },
    doctype: {
      type: String,
      required: true,
    },
    name: {
      type: [String, Number],
      required: true,
    },
    fieldname: {
      type: String,
      required: true,
    },
  },
  components: { UserProfileLink },
  resources: {
    revisions() {
      return {
        type: 'list',
        doctype: 'Version',
        fields: ['data', 'creation', 'owner'],
        orderBy: 'creation desc',
        filters: {
          ref_doctype: this.doctype,
          docname: this.name,
          data: ['like', `%"${this.fieldname}"%`],
        },
        transform(data) {
          return data.map((revision) => {
            revision.data = JSON.parse(revision.data)
            return revision
          })
        },
      }
    },
  },
  watch: {
    showDialog: {
      immediate: true,
      handler(value) {
        if (value) {
          this.$resources.revisions.list.fetch()
        }
      },
    },
  },
  setup() {
    return {
      dayjsLocal,
    }
  },
  data() {
    return {
      currentRevisionIndex: 0,
    }
  },
  methods: {
    previous() {
      let index = this.currentRevisionIndex
      index = index + 1
      if (index > this.$resources.revisions.data.length - 1) {
        index = this.$resources.revisions.data.length - 1
      }
      this.currentRevisionIndex = index
    },
    next() {
      let index = this.currentRevisionIndex
      index = index - 1
      if (index < 0) {
        index = 0
      }
      this.currentRevisionIndex = index
    },
  },
  computed: {
    title() {
      if (this.$resources.revisions.data) {
        if (this.$resources.revisions.data.length === 0) return 'No Revisions'
        if (this.$resources.revisions.data.length === 1) return '1 Revision'
        return `${this.$resources.revisions.data.length} Revisions`
      } else {
        return 'Loading...'
      }
    },
    hasPrevious() {
      if (!this.currentRevision) return false
      return this.currentRevisionIndex < this.$resources.revisions.data.length - 1
    },
    hasNext() {
      if (!this.currentRevision) return false
      return this.currentRevisionIndex > 0
    },
    currentRevision() {
      if (!this.$resources.revisions.data) {
        return null
      }
      return this.$resources.revisions.data[this.currentRevisionIndex]
    },
    htmlDiff() {
      if (!this.currentRevision) {
        return null
      }
      let change = this.currentRevision.data.changed.find((change) => change[0] === this.fieldname)
      if (!change) {
        return null
      }
      let oldHtml = change[1]
      let newHtml = change[2]

      // because of commonjs and esm shenanigans
      let makeDiff = HtmlDiff.default?.execute || HtmlDiff.execute
      return makeDiff(oldHtml, newHtml)
    },
    showDialog: {
      get() {
        return this.modelValue
      },
      set(value) {
        this.$emit('update:modelValue', value)
      },
    },
  },
}
</script>
<style>
ins {
  all: unset;
  background-color: theme('colors.green.100');
}
del {
  all: unset;
  background-color: theme('colors.red.100');
}
</style>
