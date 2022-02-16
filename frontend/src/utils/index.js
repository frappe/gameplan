import _dayjs from 'dayjs'
import relativeTime from 'dayjs/esm/plugin/relativeTime'
_dayjs.extend(relativeTime)

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
