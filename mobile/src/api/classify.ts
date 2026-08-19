import { File, UploadType } from 'expo-file-system';
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

type NativeUploadResult = {
  body: string;
  status: number;
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

function getNativeErrorMessage(result: NativeUploadResult, fallback: string): string {
  try {
    const body = JSON.parse(result.body) as ApiErrorBody;
    if (typeof body.detail === 'string' && body.detail) {
      return body.detail;
    }
  } catch {
    // Keep the fallback when the server does not return JSON.
  }

  return fallback;
}

function parseNativeScanResult(result: NativeUploadResult): ScanResult {
  try {
    return JSON.parse(result.body) as ScanResult;
  } catch {
    throw new Error('The EcoVision API returned an invalid scan response.');
  }
}

async function uploadNativeImage(asset: ImagePickerAsset): Promise<ScanResult> {
  const file = new File(asset.uri);

  if (!file.exists) {
    throw new Error('The selected image is no longer available. Please choose it again.');
  }

  let result: NativeUploadResult;

  try {
    result = await file.upload(`${API_BASE_URL}/classify`, {
      fieldName: 'file',
      httpMethod: 'POST',
      mimeType: asset.mimeType || file.type || 'image/jpeg',
      sessionType: 'foreground',
      uploadType: UploadType.MULTIPART,
    });
  } catch (error) {
    const reason = error instanceof Error && error.message ? ` ${error.message}` : '';
    throw new Error(`The selected image could not be uploaded.${reason}`);
  }

  if (result.status < 200 || result.status >= 300) {
    throw new Error(
      getNativeErrorMessage(result, `The scan failed with status ${result.status}.`),
    );
  }

  return parseNativeScanResult(result);
}

export async function classifyImage(asset: ImagePickerAsset): Promise<ScanResult> {
  if (!asset.file) {
    return uploadNativeImage(asset);
  }

  const formData = new FormData();

  formData.append('file', asset.file, getFileName(asset));

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
