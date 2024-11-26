<template>
  <div>
    <header
      class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-5 py-2.5"
    >
      <Breadcrumbs class="h-7" :items="breadcrumbs">
        <template #prefix="{ item }">
          <span class="mr-2 flex rounded-sm text-2xl leading-none" v-if="item.icon">
            {{ item.icon }}
          </span>
        </template>
      </Breadcrumbs>
      <div class="flex items-center space-x-2">
        <span class="hidden text-sm text-ink-gray-5 sm:block" v-if="page.doc">
          Last updated {{ $dayjs(page.doc.modified).format('LLL') }}
        </span>
        <Button
          v-show="page.doc && page.isDirty"
          variant="solid"
          @click="save"
          :loading="page.save.loading"
        >
          Save
        </Button>
      </div>
    </header>
    <div class="mx-auto w-full max-w-4xl px-5">
      <div class="py-6" v-if="page.doc">
        <span class="text-sm text-ink-gray-5 sm:hidden">
          Last updated {{ $dayjs(page.doc.modified).format('LLL') }}
        </span>
        <div class="mb-3 md:px-[70px]">
          <input
            class="w-full border-0 p-0 pt-4 text-3xl font-semibold focus:outline-none focus:ring-0 bg-surface-white text-ink-gray-9"
            type="text"
            :value="page.doc.title"
            @input="page.doc.title = $event.target.value"
            @keydown.enter="$refs.content.editor.commands.focus()"
            ref="titleInput"
          />
        </div>
        <TextEditor
          editor-class="rounded-b-lg max-w-[unset] prose-sm pb-[50vh] md:px-[70px]"
          :content="page.doc.content"
          @change="page.doc.content = $event"
          placeholder="Start writing here..."
          :bubbleMenu="true"
          ref="content"
        />
      </div>
    </div>
  </div>
</template>
<script>
import { Breadcrumbs, TextEditor, getCachedDocumentResource } from 'frappe-ui'
import { getTeam } from '@/data/teams'
import { getProject } from '@/data/projects'

export default {
  name: 'Page',
  props: ['pageId', 'slug'],
  components: { TextEditor, Breadcrumbs },
  resources: {
    page() {
      return {
        type: 'document',
        doctype: 'GP Page',
        name: this.pageId,
        onSuccess() {
          this.updateUrlSlug()
          this.$nextTick(() => {
            this.$refs.titleInput?.focus()
          })
        },
      }
    },
  },
  mounted() {
    document.addEventListener('keydown', this.handleKeyboardShortcuts)
  },
  beforeUnmount() {
    document.removeEventListener('keydown', this.handleKeyboardShortcuts)
  },
  methods: {
    handleKeyboardShortcuts(e) {
      if (e.key === 's' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        this.save()
      }
    },
    save() {
      this.page.save.submit(null, {
        onSuccess() {
          this.updateUrlSlug()
        },
      })
    },
    updateUrlSlug() {
      if (!this.$route.params.slug || this.$route.params.slug !== this.page.doc.slug) {
        this.$router.replace({
          name: this.page.doc.project ? 'ProjectPage' : 'Page',
          params: {
            ...this.$route.params,
            slug: this.page.doc.slug,
          },
          query: this.$route.query,
        })
      }
    },
  },
  computed: {
    page() {
      return this.$resources.page
    },
    isDirty() {
      if (!this.page.doc) return false
      return this.page.doc.title !== this.title || this.page.doc.content !== this.content
    },
    breadcrumbs() {
      if (!this.page.doc) return []
      if (!this.page.doc.project) {
        return [
          { label: 'My Pages', route: { name: 'MyPages' } },
          {
            label: this.pageTitle,
            route: {
              name: 'Page',
              params: { pageId: this.pageId, slug: this.slug },
            },
          },
        ]
      }
      let team = getTeam(this.page.doc.team)
      let project = getProject(this.page.doc.project)

      if (!(team && project)) return []
      return [
        {
          label: team.title,
          icon: team.icon,
          route: { name: 'Team', params: { teamId: team.name } },
        },
        {
          label: project.title,
          route: {
            name: 'Project',
            params: {
              teamId: team.name,
              projectId: project.name,
            },
          },
        },
        {
          label: 'Pages',
          route: {
            name: 'ProjectPages',
            params: {
              teamId: team.name,
              projectId: project.name,
            },
          },
        },
        {
          label: this.pageTitle,
          route: {
            name: 'Page',
            params: { pageId: this.pageId, slug: this.slug },
          },
        },
      ]
    },
    pageTitle() {
      let page = getCachedDocumentResource('GP Page', this.pageId)
      return page?.doc?.title || this.pageId
    },
  },
}
</script>
