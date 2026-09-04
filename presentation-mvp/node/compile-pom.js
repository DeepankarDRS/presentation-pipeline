// compile-pom.js — thin @hirokisakabe/pom wrapper with error classification.
//
// Usage:
//   node compile-pom.js <input.xml> [outputDir]              # compile to PPTX
//   node compile-pom.js --validate-only <input.xml> [outputDir]  # parseXml only
//
// Reads the XML file, runs buildPptx (or parseXml in validate-only mode), and
// writes `compile-result.json` into outputDir. On success it also writes
// `presentation.pptx` (compile mode only). Exit code is 0 on success, 1 on failure.
//
// --validate-only calls parseXml() without buildPptx(). This is faster and gives
// structured validation errors (tag/attribute/value/child/theme) without PPTX
// generation. The Python layer uses this as the primary validation step.
//
// The Python layer never parses Node stderr — it reads compile-result.json only.

import { readFile, writeFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { buildPptx, parseXml, ParseXmlError } from "@hirokisakabe/pom";

const SLIDE_SIZE = { w: 1280, h: 720 };
const POM_VERSION = "10.3.0";

const validateOnly = process.argv[2] === "--validate-only";
const inputPath = validateOnly ? process.argv[3] : process.argv[2];
const outputDir = (validateOnly ? process.argv[4] : process.argv[3]) || "./output";

/**
 * Classify a thrown error into one of the three confirmed POM error shapes.
 * Returns an array of { type, message } diagnostics.
 */
function classifyError(error) {
  // Type 1 & 2: ParseXmlError carries a machine-parseable `errors` string[].
  if (error && error.name === "ParseXmlError" && Array.isArray(error.errors)) {
    return error.errors.map((e) => {
      if (e.startsWith("Unknown tag:")) {
        return { type: "UNKNOWN_TAG", message: e };
      }
      if (e.includes("Unknown attribute")) {
        return { type: "UNKNOWN_ATTRIBUTE", message: e };
      }
      return { type: "PARSE_ERROR", message: e };
    });
  }

  // DiagnosticsError: layout-stage problems (out of bounds, overlap, etc.).
  if (error && error.name === "DiagnosticsError" && Array.isArray(error.diagnostics)) {
    return error.diagnostics.map((d) => ({
      type: "DIAGNOSTIC",
      message: d.code ? `${d.code}: ${d.message}` : d.message,
    }));
  }

  const message = error && error.message ? error.message : String(error);

  // Type 3: render-stage value errors (zero / negative / non-finite dimensions).
  if (message.includes("must be a finite positive")) {
    return [{ type: "INVALID_VALUE", message }];
  }

  return [{ type: "RENDER_ERROR", message }];
}

/**
 * Print a one-line human summary to stderr. The JSON file remains the source of
 * truth for the Python subprocess caller; this is purely for manual runs.
 */
function printSummary(result, resultPath) {
  if (result.status === "success") {
    let line = `✅ success → ${result.pptxPath || "(no pptx)"}`;
    if (result.warnings && result.warnings.length > 0) {
      line += ` (${result.warnings.length} warning${result.warnings.length > 1 ? "s" : ""}: ${result.warnings
        .map((w) => w.code)
        .join(", ")})`;
    }
    process.stderr.write(line + "\n");
  } else {
    const first = result.diagnostics && result.diagnostics[0];
    const type = first ? first.type : "UNKNOWN";
    const msg = first ? first.message : "no diagnostics";
    const extra = result.diagnostics && result.diagnostics.length > 1 ? ` (+${result.diagnostics.length - 1} more)` : "";
    process.stderr.write(`❌ failure: ${type} — ${msg}${extra}\n`);
  }
  process.stderr.write(`   result: ${resultPath}\n`);
}

/**
 * Validate-only mode: call parseXml() without buildPptx().
 * Returns structured validation errors without generating a PPTX.
 */
async function validate() {
  const result = {
    status: null,
    mode: "validate-only",
    inputPath: inputPath ? path.resolve(inputPath) : null,
    diagnostics: [],
    warnings: [],
    pomVersion: POM_VERSION,
  };

  await mkdir(outputDir, { recursive: true });
  const resultPath = path.join(outputDir, "compile-result.json");

  const writeResult = async () => {
    await writeFile(resultPath, JSON.stringify(result, null, 2), "utf8");
    if (result.status === "success") {
      process.stderr.write(`✅ parseXml valid → ${resultPath}\n`);
    } else {
      const first = result.diagnostics && result.diagnostics[0];
      const type = first ? first.type : "UNKNOWN";
      const msg = first ? first.message : "no diagnostics";
      const extra = result.diagnostics && result.diagnostics.length > 1 ? ` (+${result.diagnostics.length - 1} more)` : "";
      process.stderr.write(`❌ parseXml failed: ${type} — ${msg}${extra}\n`);
    }
    process.stderr.write(`   result: ${resultPath}\n`);
  };

  if (!inputPath) {
    result.status = "failure";
    result.diagnostics = [
      { type: "USAGE_ERROR", message: "No input XML path. Usage: node compile-pom.js --validate-only <input.xml> [outputDir]" },
    ];
    await writeResult();
    process.exit(1);
    return;
  }

  let xml;
  try {
    xml = await readFile(inputPath, "utf8");
  } catch (error) {
    result.status = "failure";
    result.diagnostics = [
      { type: "IO_ERROR", message: `Could not read input file: ${error.message}` },
    ];
    await writeResult();
    process.exit(1);
    return;
  }

  try {
    parseXml(xml);
    result.status = "success";
  } catch (error) {
    result.status = "failure";
    if (error instanceof ParseXmlError && Array.isArray(error.errors)) {
      result.diagnostics = error.errors.map((e) => {
        if (e.startsWith("Unknown tag:")) {
          return { type: "UNKNOWN_TAG", message: e };
        }
        if (e.includes("Unknown attribute")) {
          return { type: "UNKNOWN_ATTRIBUTE", message: e };
        }
        if (e.includes("Invalid value") || e.includes("Cannot convert") || e.includes("Invalid input")) {
          return { type: "INVALID_VALUE", message: e };
        }
        if (e.includes("Unknown child element")) {
          return { type: "INVALID_CHILD", message: e };
        }
        if (e.includes("theme token") || e.includes("Theme token") || e.includes("no <Theme>")) {
          return { type: "THEME_ERROR", message: e };
        }
        return { type: "PARSE_ERROR", message: e };
      });
    } else {
      result.diagnostics = classifyError(error);
    }
    result.errorName = error && error.name ? error.name : "Error";
  }

  await writeResult();
  process.exit(result.status === "success" ? 0 : 1);
}

async function compile() {
  const result = {
    status: null,
    inputPath: inputPath ? path.resolve(inputPath) : null,
    pptxPath: null,
    diagnostics: [],
    warnings: [],
    pomVersion: POM_VERSION,
    slideSize: SLIDE_SIZE,
  };

  await mkdir(outputDir, { recursive: true });
  const resultPath = path.join(outputDir, "compile-result.json");

  const writeResult = async () => {
    await writeFile(resultPath, JSON.stringify(result, null, 2), "utf8");
    printSummary(result, resultPath);
  };

  if (!inputPath) {
    result.status = "failure";
    result.diagnostics = [
      { type: "USAGE_ERROR", message: "No input XML path provided. Usage: node compile-pom.js <input.xml> [outputDir]" },
    ];
    await writeResult();
    process.exit(1);
    return;
  }

  let xml;
  try {
    xml = await readFile(inputPath, "utf8");
  } catch (error) {
    result.status = "failure";
    result.diagnostics = [
      { type: "IO_ERROR", message: `Could not read input file: ${error.message}` },
    ];
    await writeResult();
    process.exit(1);
    return;
  }

  try {
    const { pptx, diagnostics } = await buildPptx(xml, SLIDE_SIZE);

    if (Array.isArray(diagnostics) && diagnostics.length > 0) {
      result.warnings = diagnostics.map((d) => ({
        code: d.code,
        message: d.message,
      }));
    }

    const pptxPath = path.join(outputDir, "presentation.pptx");
    await pptx.writeFile({ fileName: pptxPath });

    result.status = "success";
    result.pptxPath = path.resolve(pptxPath);
  } catch (error) {
    result.status = "failure";
    result.diagnostics = classifyError(error);
    result.errorName = error && error.name ? error.name : "Error";
  }

  await writeResult();
  process.exit(result.status === "success" ? 0 : 1);
}

const main = validateOnly ? validate : compile;
main().catch(async (error) => {
  // Last-resort guard so we always leave a compile-result.json behind.
  try {
    await mkdir(outputDir, { recursive: true });
    await writeFile(
      path.join(outputDir, "compile-result.json"),
      JSON.stringify(
        {
          status: "failure",
          diagnostics: [{ type: "HARNESS_ERROR", message: error && error.message ? error.message : String(error) }],
          pomVersion: POM_VERSION,
        },
        null,
        2,
      ),
      "utf8",
    );
  } catch {
    // ignore
  }
  process.exit(1);
});
