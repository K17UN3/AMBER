import { createWorker, OEM, PSM } from "tesseract.js";
import type { LoggerMessage, Worker } from "tesseract.js";

import type { ClientOCRResult, ReceiptOCRResult } from "../types";
import {
  createSerialTaskQueue,
  raceWithAbort,
} from "../utils/serialTaskQueue";

type ProgressListener = (message: LoggerMessage) => void;

const totalKeywords = /(?:合\s*(?:計|言\s*[十ニ二])|言\s*[十ニ二]|お\s*買\s*上(?:げ)?\s*金\s*額|ご\s*請\s*求\s*額|現\s*計|総\s*額)/;
const datePattern = /(?<year>20\d{2})\s*(?:\/|\.|年)\s*(?<month>\d{1,2})\s*(?:\/|\.|月)\s*(?<day>\d{1,2})(?:日)?/;
const currencyAmountPattern = /(?:¥|￥|\\|Y)\s*([0-9]{1,3}(?:[,.]\s?[0-9]{3})+|[0-9]+)/gi;
const plainAmountPattern = /(?:^|[^0-9])([0-9]{1,3}(?:[,.]\s?[0-9]{3})+|[0-9]+)(?![0-9])/g;
const nonTotalAmountLine = /(?:現\s*金|お\s*預|預\s*り|釣|お\s*つ\s*り|消費\s*税|税\s*額)/;
const maxReceiptImageSide = 2200;
const maxReceiptImagePixels = 4_000_000;

let progressListener: ProgressListener | null = null;
let workerPromise: Promise<Worker> | null = null;
let recognitionPass = 0;
const enqueueOcr = createSerialTaskQueue();

function getWorker() {
  if (!workerPromise) {
    workerPromise = createWorker(["jpn", "eng"], OEM.LSTM_ONLY, {
      logger: (message) => {
        if (message.status !== "recognizing text") {
          progressListener?.({
            ...message,
            progress: message.progress * 0.1,
          });
          return;
        }
        const offset = recognitionPass === 1 ? 0.1 : 0.55;
        progressListener?.({
          ...message,
          progress: offset + message.progress * 0.45,
        });
      },
    }).catch((error) => {
      workerPromise = null;
      throw error;
    });
  }
  return workerPromise;
}

export function runReceiptOcr(
  image: File,
  onProgress?: ProgressListener,
  signal?: AbortSignal,
): Promise<ReceiptOCRResult> {
  return enqueueOcr(
    () => runReceiptOcrExclusive(image, onProgress, signal),
    signal,
  );
}

async function runReceiptOcrExclusive(
  image: File,
  onProgress?: ProgressListener,
  signal?: AbortSignal,
): Promise<ReceiptOCRResult> {
  progressListener = onProgress ?? null;
  let preparedImage: HTMLCanvasElement | null = null;
  let worker: Worker | null = null;
  const handleAbort = () => {
    if (!worker) {
      return;
    }
    workerPromise = null;
    void worker.terminate().catch(() => undefined);
  };

  try {
    throwIfAborted(signal);
    worker = await raceWithAbort(getWorker(), signal);
    throwIfAborted(signal);
    signal?.addEventListener("abort", handleAbort, { once: true });
    preparedImage = await prepareReceiptImage(image);
    throwIfAborted(signal);
    await raceWithAbort(
      worker.setParameters({
        tessedit_pageseg_mode: PSM.AUTO,
        preserve_interword_spaces: "0",
      }),
      signal,
    );
    recognitionPass = 1;
    const originalResult = await raceWithAbort(
      worker.recognize(
        preparedImage,
        {},
        { text: true, blocks: true },
      ),
      signal,
    );
    throwIfAborted(signal);

    let enhancedResult: Tesseract.RecognizeResult | null = null;
    try {
      enhanceReceiptImage(preparedImage);
      await raceWithAbort(
        worker.setParameters({
          tessedit_pageseg_mode: PSM.SINGLE_BLOCK,
          preserve_interword_spaces: "1",
          user_defined_dpi: "300",
        }),
        signal,
      );
      recognitionPass = 2;
      enhancedResult = await raceWithAbort(
        worker.recognize(
          preparedImage,
          { rotateAuto: true },
          { text: true, blocks: true },
        ),
        signal,
      );
    } catch (error) {
      if (signal?.aborted) {
        throw signal.reason ?? error;
      }
      // The original pass remains usable if browser image preprocessing or
      // the second recognition pass is unavailable.
    } finally {
      if (!signal?.aborted) {
        try {
          await raceWithAbort(
            worker.setParameters({
              tessedit_pageseg_mode: PSM.AUTO,
              preserve_interword_spaces: "0",
            }),
            signal,
          );
        } catch {
          // The next run configures the page segmentation mode again.
        }
      }
    }
    throwIfAborted(signal);

    const originalText = originalResult.data.text.trim();
    const enhancedText = enhancedResult?.data.text.trim() ?? "";
    const extractionText = [enhancedText, originalText].filter(Boolean).join("\n");
    const originalLines = extractLines(originalResult.data, originalText);
    const enhancedLines = enhancedResult
      ? extractLines(enhancedResult.data, enhancedText)
      : [];
    const rawText = enhancedText.length > originalText.length ? enhancedText : originalText;
    const confidence = enhancedResult
      ? (originalResult.data.confidence + enhancedResult.data.confidence) / 2
      : originalResult.data.confidence;

    return {
      shop_name:
        extractShopName(originalLines) ??
        extractShopName(enhancedLines),
      purchased_at: extractPurchasedAt(extractionText),
      total_amount:
        extractTotalAmount(enhancedText) ??
        extractTotalAmount(originalText),
      raw_ocr_text: rawText,
      confidence,
      engine: "tesseract.js",
    };
  } finally {
    signal?.removeEventListener("abort", handleAbort);
    if (preparedImage) {
      preparedImage.width = 0;
      preparedImage.height = 0;
    }
    recognitionPass = 0;
    if (progressListener === onProgress) {
      progressListener = null;
    }
  }
}

function throwIfAborted(signal?: AbortSignal) {
  if (signal?.aborted) {
    throw signal.reason ?? new DOMException("OCR解析を中止しました。", "AbortError");
  }
}

export type OCRLine = {
  text: string;
  confidence: number;
};

function extractLines(data: Tesseract.Page, rawText: string): OCRLine[] {
  const detectedLines =
    data.blocks?.flatMap((block) =>
      block.paragraphs.flatMap((paragraph) =>
        paragraph.lines.map((line) => ({
          text: line.text.trim(),
          confidence: line.confidence,
        })),
      ),
    ) ?? [];

  if (detectedLines.length > 0) {
    return detectedLines.filter((line) => line.text.length > 0);
  }

  return rawText
    .split(/\r?\n/)
    .map((text) => ({ text: text.trim(), confidence: data.confidence }))
    .filter((line) => line.text.length > 0);
}

export function extractShopName(lines: OCRLine[]) {
  const candidates = lines.slice(0, 8).filter(({ text }) => {
    if (!text || datePattern.test(text) || totalKeywords.test(text)) {
      return false;
    }
    if (/(?:TEL|〒|領収書|レシート|営業時間|\d{2,4}[-ー]\d{2,4}|[都道府県市区町丁目番地])/i.test(text)) {
      return false;
    }
    return (text.match(/[A-Za-zァ-ヶ一-龯々〆ヵヶ]/g) ?? []).length >= 2;
  });

  if (candidates.length === 0) {
    return null;
  }

  const selected = candidates.reduce((best, current) =>
    current.confidence > best.confidence ? current : best,
  ).text;

  return cleanShopName(selected).slice(0, 255);
}

export function extractPurchasedAt(rawText: string) {
  const match = datePattern.exec(rawText);
  if (!match?.groups) {
    return null;
  }

  const year = Number(match.groups.year);
  const month = Number(match.groups.month);
  const day = Number(match.groups.day);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  if (
    parsed.getUTCFullYear() !== year ||
    parsed.getUTCMonth() !== month - 1 ||
    parsed.getUTCDate() !== day
  ) {
    return null;
  }

  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

export function extractTotalAmount(rawText: string) {
  const lines = rawText.split(/\r?\n/).map((line) => line.normalize("NFKC"));

  for (const [index, line] of lines.entries()) {
    if (!totalKeywords.test(line)) {
      continue;
    }

    const sameLineAmounts = extractContextualAmounts(line);
    const plausibleSameLineAmounts = sameLineAmounts.filter((amount) => amount >= 100);
    if (plausibleSameLineAmounts.length > 0) {
      return Math.max(...plausibleSameLineAmounts);
    }

    const nearbyLines = [lines[index + 1]].filter(
      (nearby): nearby is string =>
        nearby !== undefined && !nonTotalAmountLine.test(nearby),
    );
    const nearbyAmounts = nearbyLines
      .flatMap(extractContextualAmounts)
      .filter((amount) => amount >= 100);
    if (nearbyAmounts.length > 0) {
      return Math.max(...nearbyAmounts);
    }
  }

  for (const line of lines) {
    if (/(?:%|％)\s*(?:対象|対|TH|T\s*H)/i.test(line)) {
      const amounts = extractCurrencyAmounts(line);
      if (amounts.length > 0) {
        return Math.max(...amounts);
      }
    }
  }

  return extractRepeatedCurrencyAmount(lines);
}

export function toClientOCRResult(result: ReceiptOCRResult): ClientOCRResult {
  return { ...result };
}

function cleanShopName(value: string) {
  const normalized = value.normalize("NFKC").trim();
  const withoutLeadingNoise = normalized.replace(
    /^[^A-Za-zァ-ヶ一-龯々〆ヵヶ0-9]+/,
    "",
  );
  return withoutLeadingNoise.replace(/\s+/g, " ").trim();
}

function extractCurrencyAmounts(line: string) {
  return [...line.matchAll(currencyAmountPattern)]
    .map((match) => Number(match[1].replace(/[\s,.]/g, "")))
    .filter((amount) => Number.isSafeInteger(amount) && amount > 0);
}

function extractContextualAmounts(line: string) {
  const amounts = [
    ...extractCurrencyAmounts(line),
    ...[...line.matchAll(plainAmountPattern)].map((match) =>
      Number(match[1].replace(/[\s,.]/g, "")),
    ),
  ];
  return [...new Set(amounts)].filter(
    (amount) => Number.isSafeInteger(amount) && amount > 0,
  );
}

function extractRepeatedCurrencyAmount(lines: string[]) {
  const counts = new Map<number, number>();

  for (const line of lines) {
    if (nonTotalAmountLine.test(line)) {
      continue;
    }
    for (const amount of new Set(extractCurrencyAmounts(line))) {
      counts.set(amount, (counts.get(amount) ?? 0) + 1);
    }
  }

  const repeated = [...counts.entries()]
    .filter(([, count]) => count >= 2)
    .sort(([amountA, countA], [amountB, countB]) =>
      countB - countA || amountB - amountA,
    );

  return repeated[0]?.[0] ?? null;
}

export function calculateReceiptImageSize(width: number, height: number) {
  if (
    !Number.isFinite(width) ||
    !Number.isFinite(height) ||
    width <= 0 ||
    height <= 0
  ) {
    throw new Error("画像の大きさを取得できませんでした。");
  }

  const maxSideScale = maxReceiptImageSide / Math.max(width, height);
  const pixelScale = Math.sqrt(maxReceiptImagePixels / (width * height));
  const scale = Math.min(1, maxSideScale, pixelScale);
  return {
    width: Math.max(1, Math.floor(width * scale)),
    height: Math.max(1, Math.floor(height * scale)),
  };
}

async function prepareReceiptImage(image: File) {
  const bitmap = await createImageBitmap(image, {
    imageOrientation: "from-image",
  });
  const size = calculateReceiptImageSize(bitmap.width, bitmap.height);
  const canvas = document.createElement("canvas");
  canvas.width = size.width;
  canvas.height = size.height;

  const context = canvas.getContext("2d");
  if (!context) {
    bitmap.close();
    throw new Error("画像の前処理を開始できませんでした。");
  }

  try {
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  } finally {
    bitmap.close();
  }

  return canvas;
}

function enhanceReceiptImage(canvas: HTMLCanvasElement) {
  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (!context) {
    throw new Error("画像の前処理を開始できませんでした。");
  }

  const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
  const pixels = imageData.data;
  for (let index = 0; index < pixels.length; index += 4) {
    const luminance =
      pixels[index] * 0.299 +
      pixels[index + 1] * 0.587 +
      pixels[index + 2] * 0.114;
    const contrasted = Math.max(0, Math.min(255, (luminance - 128) * 1.45 + 128));
    pixels[index] = contrasted;
    pixels[index + 1] = contrasted;
    pixels[index + 2] = contrasted;
  }
  context.putImageData(imageData, 0, 0);
}
