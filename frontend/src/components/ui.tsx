import { useId, useRef, type KeyboardEvent, type ReactNode } from "react";
import { ApiError } from "../lib/api";
import { useApp } from "../context";

export function Num({ children }: { children: ReactNode }) {
  return (
    <bdi dir="ltr" className="num">
      {children}
    </bdi>
  );
}

export interface SegOption<V extends string | number> {
  value: V;
  label: string;
}

/** Accessible radio-group segmented control with arrow-key navigation. */
export function Segmented<V extends string | number>(props: {
  label: string;
  value: V;
  options: SegOption<V>[];
  onChange: (v: V) => void;
  hideLabel?: boolean;
}) {
  const id = useId();
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const { rtl } = useApp();
  const idx = props.options.findIndex((o) => o.value === props.value);

  const onKey = (e: KeyboardEvent) => {
    const fwd = rtl ? "ArrowLeft" : "ArrowRight";
    const back = rtl ? "ArrowRight" : "ArrowLeft";
    let next = -1;
    if (e.key === fwd || e.key === "ArrowDown") next = (idx + 1) % props.options.length;
    else if (e.key === back || e.key === "ArrowUp") next = (idx - 1 + props.options.length) % props.options.length;
    else return;
    e.preventDefault();
    const opt = props.options[next];
    if (opt) {
      props.onChange(opt.value);
      refs.current[next]?.focus();
    }
  };

  return (
    <div className="field">
      <span className={props.hideLabel ? "sr-only" : "field__label"} id={`${id}-l`}>
        {props.label}
      </span>
      <div className="seg" role="radiogroup" aria-labelledby={`${id}-l`} onKeyDown={onKey}>
        {props.options.map((o, i) => (
          <button
            key={String(o.value)}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="radio"
            aria-checked={o.value === props.value}
            tabIndex={o.value === props.value ? 0 : -1}
            className="seg__btn"
            onClick={() => props.onChange(o.value)}
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function SelectField<V extends string>(props: {
  label: string;
  value: V;
  options: SegOption<V>[];
  onChange: (v: V) => void;
}) {
  const id = useId();
  return (
    <div className="field">
      <label className="field__label" htmlFor={id}>
        {props.label}
      </label>
      <select id={id} className="select" value={props.value} onChange={(e) => props.onChange(e.target.value as V)}>
        {props.options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export function Badge({ tone, children }: { tone?: "ok" | "warn" | "bad" | "muted"; children: ReactNode }) {
  return <span className={`badge${tone ? ` badge--${tone}` : ""}`}>{children}</span>;
}

export function Callout({ title, tone, children, id }: { title?: string; tone?: "info" | "warn"; children: ReactNode; id?: string }) {
  return (
    <div className={`callout${tone ? ` callout--${tone}` : ""}`} id={id} role="note">
      {title && <div className="callout__title">{title}</div>}
      <div>{children}</div>
    </div>
  );
}

export function PageHead(props: { eyebrow: string; title: string; lead?: string }) {
  return (
    <header className="page-head">
      <span className="eyebrow">{props.eyebrow}</span>
      <h1>{props.title}</h1>
      {props.lead && <p className="lead">{props.lead}</p>}
    </header>
  );
}

export function Loading({ height = 220 }: { height?: number }) {
  const { t } = useApp();
  return (
    <div className="skeleton" style={{ minHeight: height }} role="status" aria-label={t("common.loading")}>
      <span className="sr-only">{t("common.loading")}</span>
    </div>
  );
}

export function ErrorBox({ error, onRetry }: { error: ApiError; onRetry?: () => void }) {
  const { t } = useApp();
  const msg =
    error.status === 0
      ? t("common.errNetwork")
      : error.code === "results_unavailable"
        ? t("common.errResults")
        : t("common.errGeneric", { msg: error.message });
  return (
    <div className="errorbox" role="alert">
      <strong>{t("common.error")}</strong>
      <span>{msg}</span>
      {onRetry && (
        <button className="btn" type="button" onClick={onRetry}>
          {t("common.retry")}
        </button>
      )}
    </div>
  );
}

export function StatusBadge({ status }: { status: "pass" | "warn" | "fail" }) {
  const { t } = useApp();
  const tone = status === "pass" ? "ok" : status === "warn" ? "warn" : "bad";
  return <Badge tone={tone}>{t(`dq.status.${status}` as const)}</Badge>;
}
