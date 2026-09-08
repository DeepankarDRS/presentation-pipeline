// screenshot-pom.js — PPTX-to-PNG screenshot service.
//
// Usage:
//   node screenshot-pom.js <pptx-path> <output-dir>
//
// Converts each slide in the PPTX to a PNG image using the same pipeline
// as POM's own VRT tooling: soffice (LibreOffice) → PDF → ImageMagick → PNG.
//
// Writes `screenshot-result.json` into output-dir with:
//   { ok, slides: [{ index, pngPath }], error?, backend }
//
// Exit code: 0 on success, 1 on failure.

import { execSync } from "node:child_process";
import { existsSync, mkdirSync, readdirSync, copyFileSync, rmSync } from "node:fs";
import { writeFile } from "node:fs/promises";
import path from "node:path";

const pptxPath = process.argv[2];
const outputDir = process.argv[3] || "./output";

function findExecutable(names) {
  for (const name of names) {
    try {
      execSync(`where ${name}`, { stdio: "ignore" });
      return name;
    } catch {
      // not found
    }
  }
  return null;
}

function findSoffice() {
  const found = findExecutable(["soffice"]);
  if (found) return found;

  const candidates = [
    "C:\\Program Files\\LibreOffice\\program\\soffice.exe",
    "C:\\Program Files (x86)\\LibreOffice\\program\\soffice.exe",
    "/usr/bin/soffice",
    "/usr/local/bin/soffice",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
  ];
  for (const c of candidates) {
    if (existsSync(c)) return `"${c}"`;
  }
  return null;
}

function isRealImageMagick(name) {
  // On Windows, "convert" also resolves to C:\Windows\System32\convert.exe
  // (the FAT->NTFS volume converter) — must not be mistaken for ImageMagick.
  try {
    const out = execSync(`${name} -version`, { stdio: ["ignore", "pipe", "ignore"] }).toString();
    return out.includes("ImageMagick");
  } catch {
    return false;
  }
}

function findImageMagick() {
  // ImageMagick 7 uses "magick", IM6 uses "convert"
  for (const name of ["magick", "convert"]) {
    try {
      execSync(`where ${name}`, { stdio: "ignore" });
      if (isRealImageMagick(name)) return name;
    } catch {
      // not found or not a real ImageMagick binary
    }
  }
  return null;
}

async function main() {
  const result = {
    ok: false,
    slides: [],
    error: null,
    backend: "libreoffice+imagemagick",
    pptxPath: pptxPath ? path.resolve(pptxPath) : null,
  };

  mkdirSync(outputDir, { recursive: true });
  const resultPath = path.join(outputDir, "screenshot-result.json");

  const writeResult = async () => {
    await writeFile(resultPath, JSON.stringify(result, null, 2), "utf8");
  };

  if (!pptxPath) {
    result.error = "No PPTX path provided. Usage: node screenshot-pom.js <pptx> <outputDir>";
    await writeResult();
    process.exit(1);
    return;
  }

  if (!existsSync(pptxPath)) {
    result.error = `PPTX file not found: ${pptxPath}`;
    await writeResult();
    process.exit(1);
    return;
  }

  const soffice = process.env.LIBREOFFICE_BIN || findSoffice();
  if (!soffice) {
    result.error = "LibreOffice (soffice) not found. Install LibreOffice or set LIBREOFFICE_BIN.";
    await writeResult();
    process.exit(1);
    return;
  }

  const magick = process.env.IMAGEMAGICK_BIN || findImageMagick();
  if (!magick) {
    result.error = "ImageMagick not found. Install ImageMagick or set IMAGEMAGICK_BIN.";
    await writeResult();
    process.exit(1);
    return;
  }

  const tempDir = path.join(outputDir, ".screenshot-temp");
  if (existsSync(tempDir)) {
    rmSync(tempDir, { recursive: true });
  }
  mkdirSync(tempDir, { recursive: true });

  try {
    // Step 1: PPTX → PDF via LibreOffice
    const absPptx = path.resolve(pptxPath);
    // -env:UserInstallation gives this invocation its own profile. Without it,
    // consecutive soffice --headless calls share the default profile's lock —
    // if the previous call's soffice.bin hasn't fully released it yet (LibreOffice
    // is slow to tear down), the next call hangs or fails with no useful error.
    const profileDir = path.join(tempDir, ".lo-profile");
    const profileUrl = "file:///" + path.resolve(profileDir).replace(/\\/g, "/");
    execSync(
      `${soffice} --headless --norestore -env:UserInstallation=${profileUrl} ` +
      `--convert-to pdf --outdir "${tempDir}" "${absPptx}"`,
      { stdio: "pipe", timeout: 60_000 },
    );

    const pptxBasename = path.basename(pptxPath, path.extname(pptxPath));
    const pdfPath = path.join(tempDir, `${pptxBasename}.pdf`);

    if (!existsSync(pdfPath)) {
      result.error = `PDF not generated at ${pdfPath}`;
      await writeResult();
      process.exit(1);
      return;
    }

    // Step 2: PDF → PNG via ImageMagick
    const pngPrefix = path.join(tempDir, "slide");
    const magickCmd =
      magick === "magick"
        ? `magick -density 150 -strip "${pdfPath}" "${pngPrefix}-%03d.png"`
        : `convert -density 150 -strip "${pdfPath}" "${pngPrefix}-%03d.png"`;

    execSync(magickCmd, { stdio: "pipe", timeout: 120_000 });

    // Step 3: Collect and rename PNGs
    const pngFiles = readdirSync(tempDir)
      .filter((f) => f.startsWith("slide-") && f.endsWith(".png"))
      .sort();

    if (pngFiles.length === 0) {
      result.error = "No PNG slides generated from PDF";
      await writeResult();
      process.exit(1);
      return;
    }

    for (let i = 0; i < pngFiles.length; i++) {
      const src = path.join(tempDir, pngFiles[i]);
      const dst = path.join(outputDir, `slide-${i}.png`);
      copyFileSync(src, dst);
      result.slides.push({ index: i, pngPath: path.resolve(dst) });
    }

    result.ok = true;
  } catch (error) {
    result.error = error && error.message ? error.message : String(error);
  } finally {
    if (existsSync(tempDir)) {
      try {
        rmSync(tempDir, { recursive: true });
      } catch {
        // ignore cleanup errors
      }
    }
    await writeResult();
  }

  process.exit(result.ok ? 0 : 1);
}

main().catch(async (error) => {
  try {
    mkdirSync(outputDir, { recursive: true });
    await writeFile(
      path.join(outputDir, "screenshot-result.json"),
      JSON.stringify({
        ok: false,
        slides: [],
        error: error && error.message ? error.message : String(error),
        backend: "libreoffice+imagemagick",
      }, null, 2),
      "utf8",
    );
  } catch {
    // ignore
  }
  process.exit(1);
});
