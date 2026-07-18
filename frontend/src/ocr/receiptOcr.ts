import { createWorker, OEM } from "tesseract.js";
import type { LoggerMessage, Worker } from "tesseract.js";

import type { ClientOCRResult, ReceiptOCRResult } from "../types";

type ProgressListener = (message: LoggerMessage) => void;

const totalKeywords = /(?:合\s*(?:計|言\s*十)|お\s*買\s*上(?:げ)?\s*金\s*額|ご\s*請\s*求\s*額|現\s*計|現\s*金|総\s*額)/;
const datePattern = /(?<year>20\d{2})\s*(?:\/|\.|年)\s*(?<month>\d{1,2})\s*(?:\/|\.|月)\s*(?<day>\d{1,2})(?:日)?/;

let progressListener: ProgressListener | null = null;
let workerPromise: Promise<Worker> | null = null;

function getWorker() {
  if (!workerPromise) {
    workerPromise = createWorker(["jpn", "eng"], OEM.LSTM_ONLY, {
      logger: (message) => progressListener?.(message),
    }).catch((error) => {
      workerPromise = null;
      throw error;
    });
  }
  return workerPromise;
}

export async function runReceiptOcr(
  image: File,
  onProgress?: ProgressListener,
): Promise<ReceiptOCRResult> {
  progressListener = onProgress ?? null;

  try {
    const worker = await getWorker();
    const result = await worker.recognize(image, {}, { text: true, blocks: true });
    const rawText = result.data.text.trim();
    const lines = extractLines(result.data, rawText);

    return {
      shop_name: extractShopName(lines),
      purchased_at: extractPurchasedAt(rawText),
      total_amount: extractTotalAmount(rawText),
      raw_ocr_text: rawText,
      confidence: result.data.confidence,
      engine: "tesseract.js",
    };
  } finally {
    if (progressListener === onProgress) {
      progressListener = null;
    }
  }
}

type OCRLine = {
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

  return candidates.reduce((best, current) =>
    current.confidence > best.confidence ? current : best,
  ).text.slice(0, 255);
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

    const nearbyLines = [line, lines[index - 1], lines[index + 1]].filter(
      (nearby): nearby is string => nearby !== undefined,
    );
    for (const nearby of nearbyLines) {
      const matches = [
        ...nearby.matchAll(/(?:¥|￥)?\s*([0-9]{1,3}(?:[,.][0-9]{3})+|[0-9]+)(?![0-9])/g),
      ];
      const amount = matches.at(-1)?.[1];
      if (amount) {
        return Number(amount.replace(/[,.]/g, ""));
      }
    }
  }

  return null;
}

export function toClientOCRResult(result: ReceiptOCRResult): ClientOCRResult {
  return { ...result };
}
