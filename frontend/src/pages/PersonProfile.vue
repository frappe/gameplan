<template>
  <div class="py-6" v-if="profile">
    <div>
      <CoverImage
        :imageUrl="profile.cover_image"
        :imagePosition="profile.cover_image_position"
        :editable="$isSessionUser(profile.user)"
        @change="
          ({ imageUrl, imagePosition }) => {
            $resources.profile.setValue.submit({
              cover_image: imageUrl,
              cover_image_position: imagePosition,
            })
          }
        "
      />
      <div class="-mt-16 inline-block translate-y-0 px-10">
        <ImagePreview
          v-model:show="imagePreview.show"
          :imageUrl="imagePreview.imageUrl"
        />
        <button
          v-if="currentUser.user_image"
          @click="
            () => {
              imagePreview.imageUrl = currentUser.user_image
              imagePreview.show = true
            }
          "
          class="rounded-full bg-white outline-none focus:ring"
          :class="{ 'hover:opacity-80': $isSessionUser(profile.user) }"
        >
          <img
            class="h-32 w-32 rounded-full border-4 border-white object-cover"
            :src="currentUser.user_image"
          />
        </button>
        <button
          v-else
          @click="editDialog.show = true"
          class="h-32 w-32 rounded-full border-4 border-white bg-gray-200 text-sm text-gray-600"
          :class="{ 'hover:bg-gray-300': $isSessionUser(profile.user) }"
          :disabled="!$isSessionUser(profile.user)"
        >
          <span v-if="$isSessionUser(profile.user)"> Upload Image </span>
        </button>
      </div>
    </div>
    <div class="px-10">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-3xl font-bold leading-none text-gray-900">
            {{ $user(profile.user).full_name }}
          </h2>
          <p v-if="profile.bio" class="mt-2 text-lg">{{ profile.bio }}</p>
        </div>
        <Button
          v-if="$isSessionUser(profile.user)"
          @click="editDialog.show = true"
          appearance="minimal"
        >
          Edit Profile
        </Button>
      </div>
    </div>
    <div class="mt-4 px-10">
      <Tabs :tabs="tabs" />
      <router-view :profile="$resources.profile" />
    </div>
    <Dialog
      v-if="$isSessionUser(profile.user)"
      :options="{ title: 'Edit Profile' }"
      v-model="editDialog.show"
      @close="discard"
    >
      <template #body-content>
        <div class="space-y-4">
          <FileUploader @success="(file) => setUserImage(file.file_url)">
            <template v-slot="{ file, progress, uploading, openFileSelector }">
              <div class="flex items-center space-x-2">
                <Avatar
                  size="lg"
                  :imageURL="currentUser.user_image"
                  :label="currentUser.full_name"
                />
                <Button @click="openFileSelector">
                  {{ uploading ? `Uploading ${progress}%` : 'Upload Image' }}
                </Button>
                <Button
                  v-if="currentUser.user_image"
                  @click="setUserImage(null)"
                >
                  Remove
                </Button>
              </div>
            </template>
          </FileUploader>
          <Input label="First Name" v-model="user.first_name" />
          <Input label="Last Name" v-model="user.last_name" />
          <Input
            label="Bio"
            v-model="profile.bio"
            type="textarea"
            maxlength="280"
          />
        </div>
      </template>
      <template #actions>
        <Button appearance="primary" @click="save">Save</Button>
        <Button @click="editDialog.show = false">Discard</Button>
      </template>
    </Dialog>
  </div>
</template>
<script>
import {
  TextEditor,
  Popover,
  Avatar,
  Dialog,
  FileUploader,
  call,
} from 'frappe-ui'
import ReadmeEditor from '@/components/ReadmeEditor.vue'
import CoverImage from '@/components/CoverImage.vue'
import { sessionUser } from '@/resources/users'
import Tabs from '@/components/Tabs.vue'
import ImagePreview from '../components/ImagePreview.vue'

export default {
  name: 'PersonProfile',
  props: ['personId'],
  components: {
    TextEditor,
    ReadmeEditor,
    Popover,
    CoverImage,
    Avatar,
    Dialog,
    FileUploader,
    Tabs,
    ImagePreview,
  },
  beforeRouteEnter(to, from, next) {
    window.scrollTo(0, 0)
    if (to.params.personId == 'me') {
      call('frappe.client.get_value', {
        doctype: 'Team User Profile',
        filters: { user: sessionUser() },
        fieldname: 'name',
      }).then((r) => {
        next({ name: 'PersonProfile', params: { personId: r.name } })
      })
    } else {
      next()
    }
  },
  data() {
    return {
      editing: false,
      editDialog: { show: false },
      imagePreview: { show: false, imageUrl: null },
    }
  },
  resources: {
    profile() {
      return {
        type: 'document',
        doctype: 'Team User Profile',
        name: this.personId,
      }
    },
    user() {
      if (!this.profile || !this.$isSessionUser(this.profile.user)) return
      return {
        type: 'document',
        doctype: 'User',
        name: this.profile.user,
      }
    },
  },
  computed: {
    profile() {
      return this.$resources.profile.doc
    },
    user() {
      return this.$resources.user.doc
    },
    currentUser() {
      return this.$user(this.profile.user)
    },
    tabs() {
      return [
        {
          name: 'About me',
          route: {
            name: 'PersonProfileAboutMe',
            params: { personId: this.personId },
          },
          isActive: this.$route.name == 'PersonProfileAboutMe',
        },
        {
          name: 'Posts',
          route: {
            name: 'PersonProfilePosts',
            params: { personId: this.personId },
          },
          isActive: this.$route.name == 'PersonProfilePosts',
        },
      ]
    },
  },
  methods: {
    save() {
      this.$resources.user.setValue
        .submit({
          first_name: this.user.first_name,
          last_name: this.user.last_name,
        })
        .then(() => {
          this.$resources.profile.setValue.submit({
            bio: this.profile.bio,
          })
        })
      this.editDialog.show = false
    },
    discard() {
      this.$resources.user.reload()
      this.$resources.profile.reload()
    },
    setUserImage(url) {
      this.$resources.user.setValue.submit({ user_image: url })
      this.currentUser.user_image = url
    },
  },
  pageMeta() {
    return {
      title: [this.profile?.full_name || '', 'Profile'].join(' - '),
      emoji: '👨‍👩‍👧‍👦',
    }
  },
}
</script>
