import { RotateCcw, Save } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AXIS_TRAVEL_LIMIT_MAX_MM,
  AXIS_TRAVEL_LIMIT_MIN_MM,
  parseAxisTravelOverrides,
  SUPPORTED_AXIS_LIMIT_MODELS,
  type JogAxis,
  type JogPosition,
} from '../utils/printerMotion';
import { Button } from './Button';
import { Card, CardContent, CardHeader } from './Card';

type DraftLimits = Record<string, Record<JogAxis, string>>;

const axes: JogAxis[] = ['x', 'y', 'z'];

const toDraftLimits = (rawOverrides: string): DraftLimits => {
  const overrides = parseAxisTravelOverrides(rawOverrides);
  return SUPPORTED_AXIS_LIMIT_MODELS.reduce<DraftLimits>((result, model) => {
    const travel = overrides[model.key] ?? model.travel;
    result[model.key] = {
      x: String(travel.x),
      y: String(travel.y),
      z: String(travel.z),
    };
    return result;
  }, {});
};

const isSameTravel = (left: JogPosition, right: JogPosition) =>
  axes.every((axis) => left[axis] === right[axis]);

export function AxisLimitsSettings({
  rawOverrides,
  onSave,
}: {
  rawOverrides: string;
  onSave: (value: string) => void;
}) {
  const { t } = useTranslation();
  const [draftLimits, setDraftLimits] = useState<DraftLimits>(() => toDraftLimits(rawOverrides));

  useEffect(() => {
    setDraftLimits(toDraftLimits(rawOverrides));
  }, [rawOverrides]);

  const parsedDraft = useMemo(() => {
    const limits: Record<string, JogPosition> = {};
    let valid = true;
    for (const model of SUPPORTED_AXIS_LIMIT_MODELS) {
      const draft = draftLimits[model.key];
      const travel = axes.reduce<Partial<JogPosition>>((result, axis) => {
        const value = Number(draft?.[axis]);
        if (
          !Number.isFinite(value) ||
          value < AXIS_TRAVEL_LIMIT_MIN_MM ||
          value > AXIS_TRAVEL_LIMIT_MAX_MM
        ) {
          valid = false;
        }
        result[axis] = value;
        return result;
      }, {});
      limits[model.key] = travel as JogPosition;
    }
    return { limits, valid };
  }, [draftLimits]);

  const configuredOverrides = useMemo(() => (
    SUPPORTED_AXIS_LIMIT_MODELS.reduce<Record<string, JogPosition>>((result, model) => {
      const travel = parsedDraft.limits[model.key];
      if (!isSameTravel(travel, model.travel)) result[model.key] = travel;
      return result;
    }, {})
  ), [parsedDraft.limits]);

  const resetModel = (key: string) => {
    const model = SUPPORTED_AXIS_LIMIT_MODELS.find((entry) => entry.key === key);
    if (!model) return;
    setDraftLimits((current) => ({
      ...current,
      [key]: {
        x: String(model.travel.x),
        y: String(model.travel.y),
        z: String(model.travel.z),
      },
    }));
  };

  const resetAll = () => {
    setDraftLimits(toDraftLimits(''));
    onSave('');
  };

  return (
    <Card id="card-axis-limits">
      <CardHeader>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">{t('settings.axisLimits.title')}</h2>
            <p className="mt-1 max-w-3xl text-sm text-bambu-gray">{t('settings.axisLimits.description')}</p>
          </div>
          <Button type="button" variant="secondary" onClick={resetAll}>
            <RotateCcw className="h-4 w-4" />
            {t('settings.axisLimits.resetAll')}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="divide-y divide-bambu-dark-tertiary border-y border-bambu-dark-tertiary">
          {SUPPORTED_AXIS_LIMIT_MODELS.map((model) => {
            const custom = !isSameTravel(parsedDraft.limits[model.key], model.travel);
            return (
              <div key={model.key} className="grid gap-3 py-4 lg:grid-cols-[minmax(8rem,1fr)_repeat(3,minmax(7rem,10rem))_2.5rem] lg:items-end">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-medium text-white">{model.label}</h3>
                    {custom && (
                      <span className="rounded bg-bambu-green/15 px-1.5 py-0.5 text-xs text-bambu-green">
                        {t('settings.axisLimits.custom')}
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-bambu-gray">
                    {t('settings.axisLimits.defaultEnvelope')}: {model.travel.x} x {model.travel.y} x {model.travel.z} mm
                  </p>
                  {model.sharedNozzleEnvelope && (
                    <p className="mt-1 text-xs text-bambu-gray">
                      {t('settings.axisLimits.sharedNozzleEnvelope')}
                    </p>
                  )}
                </div>
                {axes.map((axis) => (
                  <label key={axis} className="block">
                    <span className="mb-1 block text-xs font-medium uppercase text-bambu-gray">{axis} (mm)</span>
                    <input
                      type="number"
                      min={AXIS_TRAVEL_LIMIT_MIN_MM}
                      max={AXIS_TRAVEL_LIMIT_MAX_MM}
                      step="0.5"
                      value={draftLimits[model.key]?.[axis] ?? ''}
                      onChange={(event) => setDraftLimits((current) => ({
                        ...current,
                        [model.key]: {
                          ...current[model.key],
                          [axis]: event.target.value,
                        },
                      }))}
                      aria-label={`${model.label} ${axis.toUpperCase()} ${t('settings.axisLimits.axisLimit')}`}
                      className="w-full rounded-lg border border-bambu-dark-tertiary bg-bambu-dark px-3 py-2 text-white focus:border-bambu-green focus:outline-none"
                    />
                  </label>
                ))}
                <button
                  type="button"
                  onClick={() => resetModel(model.key)}
                  aria-label={`${t('common.reset')} ${model.label}`}
                  title={`${t('common.reset')} ${model.label}`}
                  className="flex h-10 w-10 items-center justify-center rounded-lg border border-bambu-dark-tertiary text-bambu-gray transition-colors hover:border-bambu-green hover:text-bambu-green"
                >
                  <RotateCcw className="h-4 w-4" />
                </button>
              </div>
            );
          })}
        </div>
        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className={`text-sm ${parsedDraft.valid ? 'text-bambu-gray' : 'text-red-400'}`}>
            {parsedDraft.valid
              ? t('settings.axisLimits.rangeHint', { max: AXIS_TRAVEL_LIMIT_MAX_MM })
              : t('settings.axisLimits.invalid', { max: AXIS_TRAVEL_LIMIT_MAX_MM })}
          </p>
          <Button
            type="button"
            onClick={() => onSave(Object.keys(configuredOverrides).length > 0 ? JSON.stringify(configuredOverrides) : '')}
            disabled={!parsedDraft.valid}
          >
            <Save className="h-4 w-4" />
            {t('common.save')}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
