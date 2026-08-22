function isIOSLike(navigatorObject = globalThis.navigator) {
  if (!navigatorObject) return false
  const ua = String(navigatorObject.userAgent || '')
  const platform = String(navigatorObject.platform || '')
  const touchPoints = Number(navigatorObject.maxTouchPoints || 0)
  return /iPad|iPhone|iPod/i.test(ua) || (platform === 'MacIntel' && touchPoints > 1)
}

export function installIOSCameraCompatibility({ navigatorObject = globalThis.navigator, documentObject = globalThis.document } = {}) {
  const mediaDevices = navigatorObject?.mediaDevices
  if (!isIOSLike(navigatorObject) || !mediaDevices?.enumerateDevices) return false
  if (mediaDevices.__lodexIOSCameraCompatibility) return true

  const nativeEnumerateDevices = mediaDevices.enumerateDevices.bind(mediaDevices)

  mediaDevices.enumerateDevices = async (...args) => {
    const devices = await nativeEnumerateDevices(...args)

    // iOS Safari does not reliably keep front and rear camera captures alive at
    // the same time. App.vue opens the rear work camera first and then uses
    // enumerateDevices() to decide whether to attempt a second simultaneous
    // camera. During a LODEX virtual visit, expose one video input so the app
    // stays in single-camera mode. The existing camera-switch action then uses
    // RTCRtpSender.replaceTrack(), which is the reliable iPhone path.
    if (!documentObject?.querySelector?.('.virtual-modal')) return devices

    let keptVideo = false
    return devices.filter(device => {
      if (device.kind !== 'videoinput') return true
      if (keptVideo) return false
      keptVideo = true
      return true
    })
  }

  Object.defineProperty(mediaDevices, '__lodexIOSCameraCompatibility', {
    value: true,
    configurable: false,
    enumerable: false,
  })

  return true
}

export { isIOSLike }
