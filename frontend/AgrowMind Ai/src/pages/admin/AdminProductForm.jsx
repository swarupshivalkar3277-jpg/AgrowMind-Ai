import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ImagePlus, Save, UploadCloud } from "lucide-react";
import toast from "react-hot-toast";

import { createAdminProduct, getProduct, updateAdminProduct } from "../../services/authService";

const initialProduct = {
  name: "",
  category: "fertilizers",
  crop_type: "tomato",
  disease_tags: "",
  brand: "",
  manufacturer: "",
  mrp: "",
  discount: "",
  price: "",
  stock: "",
  unit: "piece",
  unit_size: "1 piece",
  sku: "",
  short_description: "",
  description: "",
  benefits: "",
  usage_instructions: "",
  precautions: "",
  tags: "",
  featured: false,
  status: "active",
  image: "",
  gallery: ["", "", "", "", ""],
  rating: 4,
};

function list(value) {
  return String(value || "").split(",").map((item) => item.trim()).filter(Boolean);
}

function normalize(form) {
  return {
    name: form.name.trim(),
    category: form.category,
    crop_type: list(form.crop_type),
    disease_tags: list(form.disease_tags),
    brand: form.brand.trim(),
    manufacturer: form.manufacturer.trim(),
    mrp: Number(form.mrp || form.price || 0),
    discount: Number(form.discount || 0),
    price: Number(form.price || 0),
    stock: Number(form.stock || 0),
    stock_quantity: Number(form.stock || 0),
    reserved_quantity: 0,
    sold_quantity: Number(form.sold_quantity || 0),
    unit: form.unit.trim(),
    unit_size: form.unit_size.trim(),
    sku: form.sku.trim(),
    short_description: form.short_description.trim(),
    description: form.description.trim(),
    benefits: list(form.benefits),
    usage_instructions: form.usage_instructions.trim(),
    precautions: form.precautions.trim(),
    tags: list(form.tags),
    featured: Boolean(form.featured),
    status: form.status,
    image: form.image.trim(),
    gallery: form.gallery.map((item) => item.trim()).filter(Boolean),
    rating: Number(form.rating || 4),
  };
}

function fileToProductImage(file) {
  const maxDimension = 1200;
  const quality = 0.82;

  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Could not read image file"));
    reader.onload = () => {
      const image = new Image();
      image.onerror = () => reject(new Error("Could not load image preview"));
      image.onload = () => {
        const scale = Math.min(1, maxDimension / Math.max(image.width, image.height));
        const canvas = document.createElement("canvas");
        canvas.width = Math.max(1, Math.round(image.width * scale));
        canvas.height = Math.max(1, Math.round(image.height * scale));
        const context = canvas.getContext("2d");
        context.drawImage(image, 0, 0, canvas.width, canvas.height);
        resolve(canvas.toDataURL("image/jpeg", quality));
      };
      image.src = reader.result;
    };
    reader.readAsDataURL(file);
  });
}

export default function AdminProductForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [form, setForm] = useState(initialProduct);
  const [saving, setSaving] = useState(false);
  const isEdit = Boolean(id);

  useEffect(() => {
    if (!id) return;
    getProduct(id).then(({ data }) => {
      const product = data.product || {};
      setForm({
        ...initialProduct,
        ...product,
        price: product.price ?? "",
        mrp: product.mrp ?? product.price ?? "",
        discount: product.discount ?? "",
        stock: product.stock ?? "",
        sold_quantity: product.sold_quantity ?? 0,
        crop_type: (product.crop_type || []).join(", "),
        disease_tags: (product.disease_tags || []).join(", "),
        benefits: (product.benefits || []).join(", "),
        tags: (product.tags || []).join(", "),
        gallery: [...(product.gallery || []), "", "", "", "", ""].slice(0, 5),
      });
    });
  }, [id]);

  const preview = useMemo(() => normalize(form), [form]);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function updateGallery(index, value) {
    setForm((current) => ({
      ...current,
      gallery: current.gallery.map((item, itemIndex) => (itemIndex === index ? value : item)),
    }));
  }

  async function captureImage(field, index, file) {
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      toast.error("Please select an image file");
      return;
    }

    try {
      const imageUrl = await fileToProductImage(file);
      if (field === "image") update("image", imageUrl);
      else updateGallery(index, imageUrl);
      toast.success("Image saved with product");
    } catch (error) {
      toast.error(error.message || "Image processing failed");
    }
  }

  async function submit(event) {
    event.preventDefault();
    setSaving(true);
    try {
      const payload = normalize(form);
      if (isEdit) await updateAdminProduct(id, payload);
      else await createAdminProduct(payload);
      toast.success(isEdit ? "Product updated" : "Product created");
      navigate("/admin/products");
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Product save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="pageStack">
      <section className="pageHero compactHero">
        <div>
          <span className="eyebrowText">Product Management</span>
          <h1>{isEdit ? "Edit product" : "Add product"}</h1>
          <p>Complete catalog data, image previews, validation, inventory, and marketplace presentation from one focused page.</p>
        </div>
      </section>

      <form className="productEditorGrid" onSubmit={submit}>
        <section className="panel formPanel">
          <h2>Core details</h2>
          <label><span>Product Name</span><input required value={form.name} onChange={(event) => update("name", event.target.value)} /></label>
          <div className="formRow">
            <label><span>Category</span><select value={form.category} onChange={(event) => update("category", event.target.value)}><option>fertilizers</option><option>seeds</option><option>trees</option><option>pesticides</option><option>tools</option></select></label>
            <label><span>Crop</span><input placeholder="tomato, mango" value={form.crop_type} onChange={(event) => update("crop_type", event.target.value)} /></label>
          </div>
          <label><span>Disease</span><input placeholder="early_blight, leaf_spot" value={form.disease_tags} onChange={(event) => update("disease_tags", event.target.value)} /></label>
          <div className="formRow">
            <label><span>Brand</span><input value={form.brand} onChange={(event) => update("brand", event.target.value)} /></label>
            <label><span>Manufacturer</span><input value={form.manufacturer} onChange={(event) => update("manufacturer", event.target.value)} /></label>
          </div>
          <div className="formRow">
            <label><span>MRP</span><input min="0" type="number" value={form.mrp} onChange={(event) => update("mrp", event.target.value)} /></label>
            <label><span>Discount</span><input min="0" type="number" value={form.discount} onChange={(event) => update("discount", event.target.value)} /></label>
            <label><span>Final Price</span><input min="0" required type="number" value={form.price} onChange={(event) => update("price", event.target.value)} /></label>
          </div>
          <div className="formRow">
            <label><span>Stock</span><input min="0" required type="number" value={form.stock} onChange={(event) => update("stock", event.target.value)} /></label>
            <label><span>Unit</span><select value={form.unit} onChange={(event) => update("unit", event.target.value)}><option value="piece">Piece</option><option value="kg">Kg</option><option value="g">Gram</option><option value="liter">Liter</option><option value="ml">ML</option><option value="packet">Packet</option></select></label>
            <label><span>Pack Size</span><input placeholder="5 kg, 1 liter, 250 g" value={form.unit_size} onChange={(event) => update("unit_size", event.target.value)} /></label>
          </div>
          <div className="formRow">
            <label><span>SKU</span><input value={form.sku} onChange={(event) => update("sku", event.target.value)} /></label>
            <label><span>Rating</span><input max="5" min="0" step="0.1" type="number" value={form.rating} onChange={(event) => update("rating", event.target.value)} /></label>
          </div>
        </section>

        <section className="panel formPanel">
          <h2>Content and merchandising</h2>
          <label><span>Short Description</span><input value={form.short_description} onChange={(event) => update("short_description", event.target.value)} /></label>
          <label><span>Detailed Description</span><textarea rows="4" value={form.description} onChange={(event) => update("description", event.target.value)} /></label>
          <label><span>Benefits</span><textarea rows="3" placeholder="Comma separated" value={form.benefits} onChange={(event) => update("benefits", event.target.value)} /></label>
          <label><span>Usage Instructions</span><textarea rows="3" value={form.usage_instructions} onChange={(event) => update("usage_instructions", event.target.value)} /></label>
          <label><span>Precautions</span><textarea rows="3" value={form.precautions} onChange={(event) => update("precautions", event.target.value)} /></label>
          <label><span>Tags</span><input placeholder="organic, foliar, tomato" value={form.tags} onChange={(event) => update("tags", event.target.value)} /></label>
          <div className="formRow">
            <label className="toggleField"><input checked={form.featured} onChange={(event) => update("featured", event.target.checked)} type="checkbox" /> <span>Featured Product</span></label>
            <label><span>Product Status</span><select value={form.status} onChange={(event) => update("status", event.target.value)}><option value="active">Active</option><option value="draft">Draft</option><option value="archived">Archived</option></select></label>
          </div>
        </section>

        <section className="panel formPanel">
          <h2>Images</h2>
          <label className="dropZone imageDrop">
            {form.image ? <img alt="Main product preview" src={form.image} /> : <UploadCloud size={30} />}
            <input accept="image/*" type="file" onChange={(event) => captureImage("image", 0, event.target.files?.[0])} />
            <span>Main Product Image</span>
          </label>
          <label><span>Main image URL</span><input value={form.image} onChange={(event) => update("image", event.target.value)} /></label>
          <div className="galleryEditor">
            {form.gallery.map((item, index) => (
              <label className="gallerySlot" key={index}>
                {item ? <img alt={`Gallery ${index + 1}`} src={item} /> : <ImagePlus size={22} />}
                <input accept="image/*" type="file" onChange={(event) => captureImage("gallery", index, event.target.files?.[0])} />
                <span>Gallery Image {index + 1}</span>
                <input value={item} onChange={(event) => updateGallery(index, event.target.value)} placeholder="Image URL" />
              </label>
            ))}
          </div>
        </section>

        <aside className="panel productPreviewPanel">
          <h2>Product Preview</h2>
          <article className="productCard previewCard">
            <img alt={preview.name || "Product preview"} src={preview.image || "https://images.unsplash.com/photo-1464226184884-fa280b87c399?auto=format&fit=crop&w=900&q=80"} />
            <div className="productCardBody">
              <span className="productCategory">{preview.category}</span>
              <h3>{preview.name || "Product name"}</h3>
              <p>{preview.short_description || preview.description || "Product description preview."}</p>
              <div className="productMeta"><strong>Rs. {preview.price || 0}</strong><span>{preview.unit_size}</span><span>Stock {preview.stock || 0}</span></div>
            </div>
          </article>
          <button className="primaryButton" disabled={saving} type="submit"><Save size={17} /> {saving ? "Saving..." : "Save Product"}</button>
        </aside>
      </form>
    </main>
  );
}
