<template>
  <Dialog
    v-model="show"
    :options="{ size: 'xl', position: 'top' }"
    @after-leave="filteredOptions = []"
  >
    <template #body>
      <Combobox @update:model-value="onSelection">
        <ComboboxInput
          placeholder="Search for projects or teams"
          class="w-full border-none bg-transparent px-4 text-base text-gray-800 placeholder-gray-500 focus:ring-0"
          @input="onInput"
        />
        <ComboboxOptions
          class="max-h-96 overflow-auto border-t border-gray-100"
          static
        >
          <ComboboxOption
            v-for="option in filteredOptions"
            :key="`${option.doctype}:${option.name}`"
            v-slot="{ active }"
            :value="option"
          >
            <div
              class="flex w-full items-center px-4 py-2 text-base text-gray-900"
              :class="{ 'bg-gray-200': active }"
            >
              <span> {{ option.title }}&nbsp; </span>
              <span
                v-if="option.team"
                class="inline-flex space-x-1 text-gray-600"
              >
                <span>in</span>
                <span> {{ option.team }} </span>
                <!-- <span v-if="option.team" class="text-gray-500">&mdash;</span> -->
              </span>
              <span class="ml-auto text-gray-600">
                {{ option.type }}
              </span>
            </div>
          </ComboboxOption>
        </ComboboxOptions>
      </Combobox>
    </template>
  </Dialog>
</template>
<script>
import { ref } from 'vue'
import {
  Combobox,
  ComboboxInput,
  ComboboxOptions,
  ComboboxOption,
} from '@headlessui/vue'
import Fuse from 'fuse.js/dist/fuse.basic.esm'
import { teams, activeTeams } from '@/data/teams'
import { projects } from '@/data/projects'

let show = ref(false)

export function showCommandPalette() {
  show.value = true
}

export function hideCommandPalette() {
  show.value = false
}

export function toggleCommandPalette() {
  show.value = !show.value
}

export default {
  name: 'CommandPalette',
  data() {
    return {
      filteredOptions: [],
    }
  },
  setup() {
    return { show }
  },
  components: {
    Combobox,
    ComboboxInput,
    ComboboxOptions,
    ComboboxOption,
  },
  mounted() {
    this.makeFuse()
    this.addKeyboardShortcut()
  },
  beforeUnmount() {
    hideCommandPalette()
  },
  methods: {
    onInput(e) {
      let query = e.target.value
      if (query) {
        this.filteredOptions = this.fuse
          .search(query)
          .map((result) => result.item)
      }
    },
    onSelection(value) {
      if (value) {
        this.$router.push(value.route)
        hideCommandPalette()
      }
    },
    addKeyboardShortcut() {
      window.addEventListener('keydown', (e) => {
        if (
          e.key === 'k' &&
          (e.ctrlKey || e.metaKey) &&
          !e.target.classList.contains('ProseMirror')
        ) {
          toggleCommandPalette()
          e.preventDefault()
        }
      })
    },
    async makeFuse() {
      let list = []
      await teams.list.promise
      await projects.list.promise

      let teamsByName = {}
      for (const team of activeTeams.value) {
        teamsByName[team.name] = team
        list.push({
          doctype: 'GP Team',
          type: 'Team',
          name: team.name,
          title: team.title,
          route: {
            name: 'Team',
            params: { teamId: team.name },
          },
        })
      }
      for (const project of projects.data) {
        let team = teamsByName[project.team] || null
        list.push({
          doctype: 'Project',
          type: 'Project',
          name: project.name,
          title: project.title,
          team: team?.title,
          route: {
            name: 'Project',
            params: { teamId: project.team, projectId: project.name },
          },
        })
      }
      this.fuse = new Fuse(list, {
        keys: ['title'],
      })
    },
  },
}
</script>
