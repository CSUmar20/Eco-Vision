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
    let message = `The scan failed with status ${response.status}.`;

    try {
      const body = (await response.json()) as ApiErrorBody;
      if (typeof body.detail === 'string' && body.detail) {
        message = body.detail;
      }
    } catch {
      // Keep the status-based message when the server does not return JSON.
    }

    throw new Error(message);
  }

  return (await response.json()) as ScanResult;
}
