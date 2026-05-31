export type JogAxis = 'x' | 'y' | 'z';
export type JogPosition = Record<JogAxis, number>;

export type PrinterMotionProfile = {
  label: string;
  travel: JogPosition;
  homePosition?: JogPosition;
  invertZPosition?: boolean;
};

export type SupportedAxisLimitModel = {
  key: string;
  label: string;
  travel: JogPosition;
  sharedNozzleEnvelope?: boolean;
};

export const AXIS_TRAVEL_LIMIT_MIN_MM = 1;
export const AXIS_TRAVEL_LIMIT_MAX_MM = 1000;

const motionProfile = (
  travel: JogPosition,
  options: Omit<PrinterMotionProfile, 'label' | 'travel'> = {},
): PrinterMotionProfile => ({
  label: `${travel.x} x ${travel.y} x ${travel.z} mm`,
  travel,
  ...options,
});

const A1_MINI_MOTION_PROFILE = motionProfile(
  { x: 180, y: 180, z: 180 },
  { homePosition: { x: 90, y: 90, z: 10 }, invertZPosition: true },
);
const A1_MOTION_PROFILE = motionProfile({ x: 256, y: 256, z: 256 }, { invertZPosition: true });
const STANDARD_MOTION_PROFILE = motionProfile({ x: 256, y: 256, z: 256 });
const H2D_MOTION_PROFILE = motionProfile({ x: 325, y: 320, z: 325 });
const H2C_MOTION_PROFILE = motionProfile({ x: 305, y: 320, z: 325 });
const H2S_MOTION_PROFILE = motionProfile({ x: 340, y: 320, z: 340 });
// Dashboard jog has no requested print mode, so X2D uses the safe intersection
// shared by main-nozzle, auxiliary-nozzle, and dual-nozzle operation.
const X2D_MOTION_PROFILE = motionProfile({ x: 235.5, y: 256, z: 256 });

export const SUPPORTED_AXIS_LIMIT_MODELS: SupportedAxisLimitModel[] = [
  { key: 'A1MINI', label: 'A1 Mini', travel: A1_MINI_MOTION_PROFILE.travel },
  { key: 'A1', label: 'A1', travel: A1_MOTION_PROFILE.travel },
  { key: 'X1', label: 'X1', travel: STANDARD_MOTION_PROFILE.travel },
  { key: 'X1C', label: 'X1 Carbon', travel: STANDARD_MOTION_PROFILE.travel },
  { key: 'X1E', label: 'X1E', travel: STANDARD_MOTION_PROFILE.travel },
  { key: 'P1P', label: 'P1P', travel: STANDARD_MOTION_PROFILE.travel },
  { key: 'P1S', label: 'P1S', travel: STANDARD_MOTION_PROFILE.travel },
  { key: 'P2S', label: 'P2S', travel: STANDARD_MOTION_PROFILE.travel },
  { key: 'H2D', label: 'H2D', travel: H2D_MOTION_PROFILE.travel },
  { key: 'H2DPRO', label: 'H2D Pro', travel: H2D_MOTION_PROFILE.travel },
  { key: 'H2C', label: 'H2C', travel: H2C_MOTION_PROFILE.travel },
  { key: 'H2S', label: 'H2S', travel: H2S_MOTION_PROFILE.travel },
  { key: 'X2D', label: 'X2D', travel: X2D_MOTION_PROFILE.travel, sharedNozzleEnvelope: true },
];

const PRINTER_MOTION_PROFILES: Record<string, PrinterMotionProfile> = {
  A1MINI: A1_MINI_MOTION_PROFILE,
  A12: A1_MINI_MOTION_PROFILE,
  A04: A1_MINI_MOTION_PROFILE,
  N1: A1_MINI_MOTION_PROFILE,
  A1: A1_MOTION_PROFILE,
  A11: A1_MOTION_PROFILE,
  N2S: A1_MOTION_PROFILE,
  X1: STANDARD_MOTION_PROFILE,
  X1C: STANDARD_MOTION_PROFILE,
  X1E: STANDARD_MOTION_PROFILE,
  BLP001: STANDARD_MOTION_PROFILE,
  BLP002: STANDARD_MOTION_PROFILE,
  BLP003: STANDARD_MOTION_PROFILE,
  C11: STANDARD_MOTION_PROFILE,
  C12: STANDARD_MOTION_PROFILE,
  C13: STANDARD_MOTION_PROFILE,
  P1: STANDARD_MOTION_PROFILE,
  P1P: STANDARD_MOTION_PROFILE,
  P1S: STANDARD_MOTION_PROFILE,
  P2S: STANDARD_MOTION_PROFILE,
  N7: STANDARD_MOTION_PROFILE,
  H2D: H2D_MOTION_PROFILE,
  H2DPRO: H2D_MOTION_PROFILE,
  O1D: H2D_MOTION_PROFILE,
  O1E: H2D_MOTION_PROFILE,
  O2D: H2D_MOTION_PROFILE,
  H2C: H2C_MOTION_PROFILE,
  O1C: H2C_MOTION_PROFILE,
  O1C2: H2C_MOTION_PROFILE,
  H2S: H2S_MOTION_PROFILE,
  O1S: H2S_MOTION_PROFILE,
  X2D: X2D_MOTION_PROFILE,
  N6: X2D_MOTION_PROFILE,
};

const PRINTER_AXIS_TRAVEL_OVERRIDE_KEYS: Record<string, string> = {
  A1MINI: 'A1MINI',
  A12: 'A1MINI',
  A04: 'A1MINI',
  N1: 'A1MINI',
  A1: 'A1',
  A11: 'A1',
  N2S: 'A1',
  X1: 'X1',
  BLP002: 'X1',
  X1C: 'X1C',
  BLP001: 'X1C',
  X1E: 'X1E',
  BLP003: 'X1E',
  P1: 'P1S',
  P1P: 'P1P',
  P1S: 'P1S',
  P2S: 'P2S',
  N7: 'P2S',
  H2D: 'H2D',
  O1D: 'H2D',
  H2DPRO: 'H2DPRO',
  O1E: 'H2DPRO',
  O2D: 'H2DPRO',
  H2C: 'H2C',
  O1C: 'H2C',
  O1C2: 'H2C',
  H2S: 'H2S',
  O1S: 'H2S',
  X2D: 'X2D',
  N6: 'X2D',
};

export const normalizeMotionModel = (model: string | null | undefined): string =>
  (model ?? '').trim().toUpperCase().replace(/[\s-]/g, '');

export const parseAxisTravelOverrides = (rawOverrides: string | null | undefined): Record<string, JogPosition> => {
  if (!rawOverrides) return {};
  try {
    const parsed = JSON.parse(rawOverrides);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {};
    return Object.entries(parsed).reduce<Record<string, JogPosition>>((result, [model, limits]) => {
      if (!limits || typeof limits !== 'object' || Array.isArray(limits)) return result;
      const candidate = limits as Record<string, unknown>;
      const x = candidate.x;
      const y = candidate.y;
      const z = candidate.z;
      if (
        typeof x === 'number' && Number.isFinite(x) && x >= AXIS_TRAVEL_LIMIT_MIN_MM && x <= AXIS_TRAVEL_LIMIT_MAX_MM &&
        typeof y === 'number' && Number.isFinite(y) && y >= AXIS_TRAVEL_LIMIT_MIN_MM && y <= AXIS_TRAVEL_LIMIT_MAX_MM &&
        typeof z === 'number' && Number.isFinite(z) && z >= AXIS_TRAVEL_LIMIT_MIN_MM && z <= AXIS_TRAVEL_LIMIT_MAX_MM
      ) {
        result[normalizeMotionModel(model)] = { x, y, z };
      }
      return result;
    }, {});
  } catch {
    return {};
  }
};

export const resolveMotionProfile = (
  model: string | null | undefined,
  rawOverrides?: string | null,
): PrinterMotionProfile | null => {
  const normalized = normalizeMotionModel(model);
  const profile = PRINTER_MOTION_PROFILES[normalized];
  if (!profile) return null;

  const overrides = parseAxisTravelOverrides(rawOverrides);
  const override = overrides[normalized] ?? overrides[PRINTER_AXIS_TRAVEL_OVERRIDE_KEYS[normalized]];
  return override
    ? { ...profile, label: `${override.x} x ${override.y} x ${override.z} mm`, travel: override }
    : profile;
};

export const jogPositionDelta = (profile: PrinterMotionProfile, axis: JogAxis, distance: number): number =>
  axis === 'z' && profile.invertZPosition ? -distance : distance;
