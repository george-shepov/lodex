const DEFAULT_STORAGE_KEY = 'lodex-pending-uploads-v1'

function normalizeUpload(file) {
  if (!file?.upload_id) return null
  return {
    upload_id: String(file.upload_id),
    filename: String(file.filename || 'upload'),
    media_type: String(file.media_type || 'application/octet-stream'),
    description: String(file.description || ''),
  }
}

export function mergeProjectUploads(existing = [], pending = []) {
  const merged = []
  const positions = new Map()

  const add = file => {
    const normalized = normalizeUpload(file)
    if (!normalized) return
    const position = positions.get(normalized.upload_id)
    if (position === undefined) {
      positions.set(normalized.upload_id, merged.length)
      merged.push(normalized)
    } else {
      merged[position] = { ...merged[position], ...normalized }
    }
  }

  pending.forEach(add)
  existing.forEach(add)
  return merged
}

export function createUploadAccumulator(storage = null, storageKey = DEFAULT_STORAGE_KEY) {
  let pending = []

  try {
    const saved = storage?.getItem(storageKey)
    if (saved) pending = mergeProjectUploads([], JSON.parse(saved))
  } catch {
    pending = []
  }

  const persist = () => {
    try {
      if (!storage) return
      if (pending.length) storage.setItem(storageKey, JSON.stringify(pending))
      else storage.removeItem(storageKey)
    } catch {}
  }

  return {
    remember(file) {
      pending = mergeProjectUploads([], [...pending, file])
      persist()
      return [...pending]
    },
    enrich(payload = {}) {
      return { ...payload, uploads: mergeProjectUploads(payload.uploads || [], pending) }
    },
    clear() {
      pending = []
      persist()
    },
    list() {
      return [...pending]
    },
  }
}
