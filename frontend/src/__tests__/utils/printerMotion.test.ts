import { describe, expect, it } from 'vitest';
import { jogPositionDelta, parseAxisTravelOverrides, resolveMotionProfile } from '../../utils/printerMotion';

describe('printer motion profiles', () => {
  it('uses the official default envelope for supported display models', () => {
    expect(resolveMotionProfile('A1 Mini')?.travel).toEqual({ x: 180, y: 180, z: 180 });
    expect(resolveMotionProfile('A1')?.travel).toEqual({ x: 256, y: 256, z: 256 });
    expect(resolveMotionProfile('H2C')?.travel).toEqual({ x: 305, y: 320, z: 325 });
    expect(resolveMotionProfile('H2S')?.travel).toEqual({ x: 340, y: 320, z: 340 });
    expect(resolveMotionProfile('X2D')?.travel).toEqual({ x: 235.5, y: 256, z: 256 });
    expect(resolveMotionProfile('N6')?.travel).toEqual({ x: 235.5, y: 256, z: 256 });
  });

  it('applies a configured display-model override to its internal alias', () => {
    const overrides = JSON.stringify({ A1MINI: { x: 170, y: 171, z: 172 } });
    expect(resolveMotionProfile('N1', overrides)?.travel).toEqual({ x: 170, y: 171, z: 172 });
  });

  it('ignores malformed overrides', () => {
    expect(parseAxisTravelOverrides('{"A1MINI":{"x":0,"y":180,"z":180}}')).toEqual({});
    expect(parseAxisTravelOverrides('not json')).toEqual({});
  });

  it('tracks A1-family Z position in toolhead coordinates', () => {
    const profile = resolveMotionProfile('A1');
    expect(profile).not.toBeNull();
    expect(jogPositionDelta(profile!, 'z', 3)).toBe(-3);
  });
});
