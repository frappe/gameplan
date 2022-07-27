import _dayjs from 'dayjs'
import relativeTime from 'dayjs/esm/plugin/relativeTime'
import localizedFormat from 'dayjs/plugin/localizedFormat'
import updateLocale from 'dayjs/plugin/updateLocale'
import isToday from 'dayjs/plugin/isToday'

_dayjs.extend(updateLocale)
_dayjs.extend(relativeTime)
_dayjs.extend(localizedFormat)
_dayjs.extend(isToday)
_dayjs.updateLocale('en', {
  relativeTime: {
    future: 'in %s',
    past: '%s ago',
    s: 'a few seconds',
    m: '1m',
    mm: '%dm',
    h: '1h',
    hh: '%dh',
    d: 'd',
    dd: '%dd',
    M: '1M',
    MM: '%dM',
    y: 'y',
    yy: '%dy',
  },
})

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

export function htmlToText(html) {
  let tmp = document.createElement('div')
  tmp.innerHTML = html
  return tmp.textContent || tmp.innerText || ''
}
