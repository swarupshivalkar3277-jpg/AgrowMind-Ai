import { ImagePlus, Sparkles } from "lucide-react";

export default function UploadBox({ crop, crops, error, file, loading, onCrop, onFile, onSubmit, previewUrl }) {
  return (
    <form className="uploadBox" id="predict" onSubmit={onSubmit}>
      <div className="uploadHeader">
        <Sparkles size={22} />
        <div>
          <strong>AI Crop Diagnosis</strong>
          <span>Drag, preview, and analyze crop leaf health</span>
        </div>
      </div>
      <label className="fieldLabel">
        <span>Select crop</span>
        <select onChange={(event) => onCrop(event.target.value)} value={crop}>
          {crops.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
        </select>
      </label>
      <label className={`dropZone ${previewUrl ? "hasPreview" : ""}`}>
        {previewUrl ? <img alt="Leaf preview" src={previewUrl} /> : <ImagePlus size={34} />}
        <input accept="image/*" capture="environment" onChange={onFile} type="file" />
        <span>{file ? `${file.name} (${Math.round(file.size / 1024)}KB)` : "Drop leaf image or tap to upload"}</span>
      </label>
      {error && <div className="alert">{error}</div>}
      <button className="primaryButton" disabled={loading} type="submit">
        {loading ? "Analyzing crop..." : "Predict Disease"}
      </button>
    </form>
  );
}
