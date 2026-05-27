export async function compressImage(file, { maxBytes = 400 * 1024, maxDimension = 1280, quality = 0.78 } = {}) {
  if (!file || !file.type?.startsWith("image/") || file.size <= maxBytes) return file;

  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, maxDimension / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(bitmap.width * scale));
  canvas.height = Math.max(1, Math.round(bitmap.height * scale));
  const context = canvas.getContext("2d", { alpha: false });
  context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);

  let nextQuality = quality;
  let blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", nextQuality));
  while (blob && blob.size > maxBytes && nextQuality > 0.46) {
    nextQuality -= 0.08;
    blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", nextQuality));
  }

  if (!blob) return file;
  return new File([blob], file.name.replace(/\.[^.]+$/, ".jpg"), { type: "image/jpeg", lastModified: Date.now() });
}
