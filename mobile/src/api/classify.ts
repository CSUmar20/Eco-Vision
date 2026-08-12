import type { ImagePickerAsset } from 'expo-image-picker';

import { API_BASE_URL } from '@/config/api';

export type Prediction = {
  label: string;
  score: number;
};

export type ScanResult = {
  scan_id: string;
  created_at: string;
  model_id: string;
  top_prediction: Prediction;
  alternatives: Prediction[];
  disposal_status: 'local_rules_not_checked';
};

export type ScanConfirmation = {
  scan_id: string;
  confirmed_label: string;
};

type ApiErrorBody = {
  detail?: unknown;
};

function getFileName(asset: ImagePickerAsset): string {
  if (asset.fileName) {
    return asset.fileName;
  }

  const extension = asset.mimeType?.split('/')[1] || 'jpg';
  return `ecovision-upload.${extension}`;
}

async function getErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const body = (await response.json()) as ApiErrorBody;
    if (typeof body.detail === 'string' && body.detail) {
      return body.detail;
    }
  } catch {
    // Keep the fallback when the server does not return JSON.
  }

  return fallback;
}

export async function classifyImage(asset: ImagePickerAsset): Promise<ScanResult> {
  const formData = new FormData();

  if (asset.file) {
    formData.append('file', asset.file, getFileName(asset));
  } else {
    const nativeFile = {
      uri: asset.uri,
      name: getFileName(asset),
      type: asset.mimeType || 'image/jpeg',
    };

    formData.append('file', nativeFile as unknown as Blob);
  }

  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}/classify`, {
      method: 'POST',
      body: formData,
    });
  } catch {
    throw new Error(`Could not reach the EcoVision API at ${API_BASE_URL}.`);
  }

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response, `The scan failed with status ${response.status}.`),
    );
  }

  return (await response.json()) as ScanResult;
}

export async function confirmScan(
  scanId: string,
  confirmedLabel: string,
): Promise<ScanConfirmation> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}/scans/${scanId}/confirmation`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ confirmed_label: confirmedLabel }),
    });
  } catch {
    throw new Error(`Could not reach the EcoVision API at ${API_BASE_URL}.`);
  }

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        `The confirmation failed with status ${response.status}.`,
      ),
    );
  }

  return (await response.json()) as ScanConfirmation;
}
