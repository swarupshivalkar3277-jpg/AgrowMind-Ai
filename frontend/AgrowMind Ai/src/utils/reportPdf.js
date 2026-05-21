function escapePdfText(value) {
  return String(value ?? "")
    .replace(/\\/g, "\\\\")
    .replace(/\(/g, "\\(")
    .replace(/\)/g, "\\)");
}

function wrapLine(text, maxLength = 82) {
  const words = String(text || "").split(/\s+/).filter(Boolean);
  const lines = [];
  let current = "";

  words.forEach((word) => {
    const next = current ? `${current} ${word}` : word;
    if (next.length > maxLength && current) {
      lines.push(current);
      current = word;
    } else {
      current = next;
    }
  });

  if (current) {
    lines.push(current);
  }

  return lines.length ? lines : [""];
}

function buildPdf(lines) {
  const objects = [];
  const contentLines = ["BT", "/F1 12 Tf", "50 790 Td", "16 TL"];

  lines.forEach((line, index) => {
    if (index === 0) {
      contentLines.push("/F1 20 Tf");
    }

    contentLines.push(`(${escapePdfText(line)}) Tj`, "T*");

    if (index === 0) {
      contentLines.push("/F1 12 Tf", "T*");
    }
  });

  contentLines.push("ET");
  const content = contentLines.join("\n");

  objects.push("<< /Type /Catalog /Pages 2 0 R >>");
  objects.push("<< /Type /Pages /Kids [3 0 R] /Count 1 >>");
  objects.push("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>");
  objects.push("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>");
  objects.push(`<< /Length ${content.length} >>\nstream\n${content}\nendstream`);

  let pdf = "%PDF-1.4\n";
  const offsets = [0];

  objects.forEach((object, index) => {
    offsets.push(pdf.length);
    pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;
  });

  const xrefOffset = pdf.length;
  pdf += `xref\n0 ${objects.length + 1}\n`;
  pdf += "0000000000 65535 f \n";
  offsets.slice(1).forEach((offset) => {
    pdf += `${String(offset).padStart(10, "0")} 00000 n \n`;
  });
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`;

  return pdf;
}

export function downloadPredictionReport({ user, crop, prediction, createdAt = new Date() }) {
  const disease = prediction?.disease?.replaceAll("_", " ") || "Unknown";
  const lines = [
    "AgroMind AI Smart Farming Report",
    `User: ${user?.name || user?.email || "Farmer"}`,
    `Date/time: ${new Date(createdAt).toLocaleString()}`,
    `Crop: ${crop || "Unknown"}`,
    `Disease: ${disease}`,
    `Confidence: ${prediction?.confidence ?? "N/A"}%`,
    `Severity: ${prediction?.severity || "N/A"}`,
    `Harvest risk: ${prediction?.harvest_risk || "N/A"}`,
    "",
    "Fertilizer recommendation:",
    ...(prediction?.fertilizer || []).flatMap((item) => wrapLine(`- ${item}`)),
    "",
    "Treatment recommendation:",
    ...(prediction?.treatment || []).flatMap((item) => wrapLine(`- ${item}`)),
    "",
    "Irrigation advice:",
    ...wrapLine(prediction?.irrigation || "N/A"),
  ];

  const pdf = buildPdf(lines.slice(0, 48));
  const blob = new Blob([pdf], { type: "application/pdf" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `agromind-${crop || "crop"}-${Date.now()}.pdf`;
  link.click();
  URL.revokeObjectURL(url);
}
