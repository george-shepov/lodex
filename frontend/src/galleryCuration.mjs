export const hiddenGalleryProjectIds = new Set([
  'lz-125',
  'lz-149',
  'lz-150',
  'lz-152',
])

export function applyGalleryCuration(projects) {
  if (!Array.isArray(projects)) return projects
  for (let index = projects.length - 1; index >= 0; index -= 1) {
    if (hiddenGalleryProjectIds.has(projects[index]?.id)) projects.splice(index, 1)
  }
  return projects
}
