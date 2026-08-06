import { useFileUpload, type UploadOptions, type UploadedFile } from 'frappe-ui'

/**
 * Every kind of image Gameplan uploads, and how it should be stored.
 *
 * There is no default. A new upload site has to name its kind, because the two
 * upload primitives disagree about what happens when you say nothing: frappe-ui's
 * `FileUploader` uploads private, `useFileUpload()` uploads public. Leaving that
 * to the call site is how the same avatar ended up private on one screen and
 * public on another.
 *
 * `private: true` does not mean "only the uploader can see it". A private File is
 * readable by anyone who can read the document it is attached to. That makes the
 * attachment the thing that matters, so every kind below is listed with the
 * document its File ends up attached to, and there is a backend test proving it.
 */
export const IMAGE_UPLOAD_KINDS = {
  /** Profile photo. Attached to GP User Profile by `set_image`. */
  avatar: { private: true, optimize: true, extensions: ['png', 'jpg', 'jpeg'] },
  /** Profile or space cover. Attached to GP User Profile when the profile saves. */
  cover: { private: true, optimize: true, extensions: ['png', 'jpg', 'jpeg'] },
  /** Bento card image. Attached to GP User Profile by `attach_bento_card_images`. */
  bentoCard: { private: true, optimize: true, extensions: ['png', 'jpg', 'jpeg'] },
  /** Community image. Attached to GP Team when the community saves. */
  communityImage: { private: true, optimize: true, extensions: ['png', 'jpg', 'jpeg'] },
  /**
   * Custom emoji. Attached to GP Custom Emoji on insert. Never optimized: the
   * whole point of a party parrot is that it is still animated afterwards.
   */
  customEmoji: {
    private: true,
    optimize: false,
    extensions: ['png', 'jpg', 'jpeg', 'gif', 'webp'],
  },
} as const satisfies Record<string, ImageUploadSpec>

interface ImageUploadSpec {
  private: boolean
  optimize: boolean
  extensions: string[]
}

export type ImageUploadKind = keyof typeof IMAGE_UPLOAD_KINDS

const MIME_TYPES: Record<string, string> = {
  png: 'image/png',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  gif: 'image/gif',
  webp: 'image/webp',
}

/** Upload options for a kind, in the shape `FileUploader`'s `uploadArgs` expects. */
export function imageUploadArgs(kind: ImageUploadKind): UploadOptions {
  const spec = IMAGE_UPLOAD_KINDS[kind]
  return { private: spec.private, optimize: spec.optimize }
}

/** `accept` values for a kind, deduped so `jpg` and `jpeg` do not both appear. */
export function imageFileTypes(kind: ImageUploadKind): string[] {
  return [...new Set(IMAGE_UPLOAD_KINDS[kind].extensions.map((ext) => MIME_TYPES[ext]))]
}

/**
 * Reject a file the server would reject anyway, but before it is uploaded, so the
 * error lands next to the button instead of arriving as a failed request.
 */
export function validateImageFile(kind: ImageUploadKind, file: File): string | undefined {
  const extensions = IMAGE_UPLOAD_KINDS[kind].extensions
  const extension = file.name.split('.').pop()?.toLowerCase()
  if (!extension || !extensions.includes(extension)) {
    return `Only ${formatExtensionList(extensions)} images are allowed`
  }
}

function formatExtensionList(extensions: readonly string[]) {
  // "jpg" and "jpeg" are one choice to a reader, even though both are accepted.
  const labels = [...new Set(extensions.map((ext) => (ext === 'jpeg' ? 'jpg' : ext)))].map((ext) =>
    ext.toUpperCase(),
  )
  if (labels.length === 1) return labels[0]
  return `${labels.slice(0, -1).join(', ')} and ${labels[labels.length - 1]}`
}

/**
 * Upload an image without a file picker, for the screens that already hold a File
 * (the avatar cropper hands over a re-encoded blob). The component equivalent is
 * `ImageUploader.vue`; both read the same table above.
 */
export function useImageUpload() {
  const upload = useFileUpload()

  return {
    ...upload,
    upload: (file: File, kind: ImageUploadKind): Promise<UploadedFile> =>
      upload.upload(file, imageUploadArgs(kind)),
  }
}
