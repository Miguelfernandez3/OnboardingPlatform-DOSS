import type { Device } from '../../core/domain/entities/Device';

/** Aligned with backend enforcement_context.normalize_key */
export function normalizeEnforcementKey(key: string): string {
  return key.trim().toLowerCase().replace(/_/g, '-');
}

export function isDeviceIpKeyNormalized(normalized: string): boolean {
  return normalized === 'device-ip' || normalized === 'deviceip';
}

export type MissingItem = {
  key?: string;
  label?: string;
  sensitive?: boolean;
  source?: string;
  /** Backend: save as encrypted device bearer (API bearerToken), not only extra context */
  deviceEncryptedBearer?: boolean;
};

export function splitUpdateFromForm(
  missing: MissingItem[],
  form: Record<string, string>,
  device: Device
): {
  update: Partial<Device>;
  extraContext: Record<string, unknown>;
} {
  const extraContext: Record<string, unknown> = {};
  let ip: string | undefined;
  let bearerToken: string | undefined;
  const enc: Record<string, unknown> = {
    ...(device.enforcementContext && typeof device.enforcementContext === 'object'
      ? { ...device.enforcementContext }
      : {})
  };
  let encDirty = false;

  for (const m of missing) {
    const rawKey = m.key != null ? String(m.key) : '';
    if (!rawKey) continue;
    const val = form[rawKey];
    if (val === undefined || val === '') continue;
    const nk = normalizeEnforcementKey(rawKey);

    if (m.deviceEncryptedBearer) {
      bearerToken = val;
      continue;
    }

    if (m.sensitive || nk === 'auth-profile-secret') {
      extraContext[rawKey] = val;
      extraContext[nk] = val;
      continue;
    }
    if (isDeviceIpKeyNormalized(nk)) {
      ip = val;
      enc['device_ip'] = val;
      enc['device-ip'] = val;
      encDirty = true;
      continue;
    }
    enc[rawKey] = val;
    enc[nk] = val;
    encDirty = true;
  }

  const update: Partial<Device> = {};
  if (ip !== undefined) {
    update.ip = ip;
  }
  if (bearerToken !== undefined) {
    (update as Record<string, unknown>).bearerToken = bearerToken;
  }
  if (encDirty) {
    update.enforcementContext = enc;
  }
  return { update, extraContext };
}
