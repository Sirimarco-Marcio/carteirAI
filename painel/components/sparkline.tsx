/**
 * Sparkline "respirando": área fluida suave, sem eixos nem grade — só a linha do saldo.
 * Preenchimento em gradiente brand-soft → transparente (a assinatura visual do dashboard).
 */
export function Sparkline({
  dados,
  className = "",
  altura = 96,
}: {
  dados: number[];
  className?: string;
  altura?: number;
}) {
  const W = 600;
  const H = altura;
  const min = Math.min(...dados);
  const max = Math.max(...dados);
  const span = max - min || 1;
  const pad = 6;

  const pontos = dados.map((v, i) => {
    const x = (i / (dados.length - 1)) * W;
    const y = pad + (1 - (v - min) / span) * (H - pad * 2);
    return [x, y] as const;
  });

  // Caminho suave (Catmull-Rom → Bézier) para evitar picos serrilhados.
  const linha = pontos
    .map(([x, y], i) => {
      if (i === 0) return `M ${x},${y}`;
      const [px, py] = pontos[i - 1];
      const cx = (px + x) / 2;
      return `C ${cx},${py} ${cx},${y} ${x},${y}`;
    })
    .join(" ");

  const area = `${linha} L ${W},${H} L 0,${H} Z`;

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      className={className}
      style={{ width: "100%", height: altura }}
      aria-hidden
    >
      <defs>
        <linearGradient id="breath" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#1e6f5c" stopOpacity="0.18" />
          <stop offset="100%" stopColor="#1e6f5c" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill="url(#breath)" />
      <path d={linha} fill="none" stroke="#1e6f5c" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}
