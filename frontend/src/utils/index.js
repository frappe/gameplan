import _dayjs from 'dayjs'
import relativeTime from 'dayjs/esm/plugin/relativeTime'
import localizedFormat from 'dayjs/plugin/localizedFormat'

_dayjs.extend(relativeTime)
_dayjs.extend(localizedFormat)

export let dayjs = _dayjs

export function getImgDimensions(imgSrc) {
  return new Promise((resolve) => {
    let img = new Image()
    img.onload = function () {
      let { width, height } = img
      resolve({ width, height, ratio: width / height })
    }
    img.src = imgSrc
  })
}
