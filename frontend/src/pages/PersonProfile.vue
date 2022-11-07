<template>
  <div v-if="profile">
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
    </div>
    <div class="-mt-16 inline-flex translate-y-0 px-6">
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
        :class="{
          'hover:opacity-80': $isSessionUser(profile.user),
        }"
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
    <div class="sticky top-0 z-10 border-b bg-white px-6">
      <div class="flex items-center justify-between pt-2">
        <div class="flex items-baseline">
          <h2 class="text-3xl font-bold leading-none text-gray-900">
            {{ $user(profile.user).full_name }}
          </h2>
          <span class="px-1 text-gray-600">&middot;</span>
          <p v-if="profile.bio" class="text-lg">{{ profile.bio }}</p>
        </div>
        <Button
          v-if="$isSessionUser(profile.user)"
          @click="editDialog.show = true"
          appearance="minimal"
        >
          Edit Profile
        </Button>
      </div>
      <Tabs class="border-none" :tabs="tabs" />
    </div>
    <div class="mx-auto max-w-4xl px-5">
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
                <UserAvatar size="lg" :user="profile.user" />
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
import { Dialog, FileUploader } from 'frappe-ui'
import CoverImage from '@/components/CoverImage.vue'
import Tabs from '@/components/Tabs.vue'
import ImagePreview from '../components/ImagePreview.vue'

export default {
  name: 'PersonProfile',
  props: ['personId'],
  components: {
    CoverImage,
    Dialog,
    FileUploader,
    Tabs,
    ImagePreview,
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
