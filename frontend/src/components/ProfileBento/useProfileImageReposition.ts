import { computed, ref, watch } from 'vue'
import { getImgDimensions, type ImgDimensions } from '@/utils'

export interface ProfileImageRepositionOptions {
  imageUrl: () => string
  /** The position already on the card, as a percentage. */
  savedPosition: () => number | undefined
  /** Whether the card is in reposition mode, which is the only time a drag counts. */
  repositioning: () => boolean
  onSave: (position: number) => void
}

/**
 * Drag a cropped image up and down inside its frame to pick what stays visible.
 *
 * A card's image is `object-fit: cover`, so anything taller than the frame is
 * cropped, and which part gets cropped is one number: `object-position`. The
 * gesture turns vertical pointer travel into a change in that number, scaled so
 * that dragging the full overflow moves the image from one edge to the other —
 * the image tracks the finger rather than moving at some fixed rate.
 *
 * The working value is held apart from the saved one, so leaving reposition mode
 * without saving shows the card exactly as it was.
 */
export function useProfileImageReposition(options: ProfileImageRepositionOptions) {
  const imageFrame = ref<HTMLElement | null>(null)
  const imageDimensions = ref<ImgDimensions | null>(null)
  const draggingImage = ref(false)
  /** The unsaved position, live only while the card is being repositioned. */
  const tempImagePosition = ref(50)
  const dragStartY = ref(0)
  const dragStartPosition = ref(50)

  const currentImagePosition = computed(() => {
    if (options.repositioning()) return clampPosition(tempImagePosition.value)
    return clampPosition(options.savedPosition() ?? 50)
  })

  const imageStyle = computed(() => {
    return {
      objectPosition: `center ${currentImagePosition.value}%`,
    }
  })

  // Entering reposition mode starts from whatever is saved, so a cancelled drag
  // and a fresh one begin in the same place.
  watch(
    () => [options.repositioning(), options.savedPosition()] as const,
    ([repositioning]) => {
      if (repositioning) tempImagePosition.value = clampPosition(options.savedPosition() ?? 50)
    },
  )

  watch(
    () => options.imageUrl(),
    async (url) => {
      imageDimensions.value = url ? await getImgDimensions(url) : null
    },
    { immediate: true },
  )

  async function loadImageDimensions() {
    let url = options.imageUrl()
    if (!url) return
    imageDimensions.value = await getImgDimensions(url)
  }

  function startImageReposition(event: PointerEvent) {
    if (event.button !== 0 || isImageRepositionControl(event.target)) return
    // An image no taller than its frame is not cropped, so there is nothing to
    // choose between.
    if (!getVerticalOverflow()) return

    draggingImage.value = true
    dragStartY.value = event.clientY
    dragStartPosition.value = clampPosition(tempImagePosition.value)
    ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
  }

  /** The Save and Cancel buttons sit on the drag surface, and are not it. */
  function isImageRepositionControl(target: EventTarget | null) {
    if (!(target instanceof HTMLElement)) return false
    return Boolean(target.closest('[data-image-reposition-control]'))
  }

  function moveImageReposition(event: PointerEvent) {
    if (!draggingImage.value) return

    let verticalOverflow = getVerticalOverflow()
    if (!verticalOverflow) return

    let deltaY = dragStartY.value - event.clientY
    let deltaPosition = (deltaY * 100) / verticalOverflow
    tempImagePosition.value = clampPosition(dragStartPosition.value + deltaPosition)
  }

  function endImageReposition(event: PointerEvent) {
    if (!draggingImage.value) return

    draggingImage.value = false
    let surface = event.currentTarget as HTMLElement
    if (surface.hasPointerCapture(event.pointerId)) {
      surface.releasePointerCapture(event.pointerId)
    }
  }

  function saveImagePosition() {
    options.onSave(clampPosition(tempImagePosition.value))
  }

  /** How much of the image the frame is cropping off, in pixels. */
  function getVerticalOverflow() {
    if (!imageFrame.value) return 0

    let { width, height } = imageFrame.value.getBoundingClientRect()
    let imageRatio = getImageRatio()
    if (!imageRatio) return 0

    let imageHeight = width / imageRatio
    return Math.max(0, imageHeight - height)
  }

  /**
   * The measured ratio if it has arrived, the rendered image's own otherwise.
   *
   * `getImgDimensions` is a network round trip, so the first drag after a card
   * appears can start before it resolves. The `<img>` already knows.
   */
  function getImageRatio() {
    if (imageDimensions.value?.ratio) return imageDimensions.value.ratio

    let image = imageFrame.value?.querySelector('img')
    if (!image?.naturalWidth || !image.naturalHeight) return 0
    return image.naturalWidth / image.naturalHeight
  }

  function clampPosition(position: number) {
    return Math.min(100, Math.max(0, Number(position) || 0))
  }

  return {
    /** Bind to the element that crops the image; every measurement is its rect. */
    imageFrame,
    draggingImage,
    /** The `object-position` the image should render at, saved or in progress. */
    imageStyle,
    loadImageDimensions,
    startImageReposition,
    moveImageReposition,
    endImageReposition,
    saveImagePosition,
  }
}
