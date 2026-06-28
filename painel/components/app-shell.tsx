"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { USUARIO_ATUAL } from "@/lib/fake-data";

/** Ícones inline (currentColor). */
const ICons: Record<string, React.ReactNode> = {
  dashboard: <><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" /></>,
  extrato: <><rect x="5" y="3" width="14" height="18" rx="2" /><path d="M9 8h6M9 12h6M9 16h4" strokeLinecap="round" /></>,
  cartoes: <><rect x="2" y="6" width="20" height="13" rx="2.5" /><path d="M2 10h20" /></>,
  renda: <><circle cx="12" cy="12" r="8" /><path d="M12 8v8M9.5 10.5h3.5a1.5 1.5 0 0 1 0 3H10a1.5 1.5 0 0 0 0 3h4" strokeLinecap="round" /></>,
  relatorios: <><path d="M4 19V5M4 19h16" strokeLinecap="round" /><path d="M8 16l3-4 3 2 4-6" strokeLinecap="round" strokeLinejoin="round" /></>,
  sino: <><path d="M6 8a6 6 0 1 1 12 0c0 7 3 7 3 9H3c0-2 3-2 3-9" strokeLinecap="round" /><path d="M10.5 21a1.5 1.5 0 0 0 3 0" /></>,
  mais: <path d="M12 5v14M5 12h14" strokeLinecap="round" />,
};

function Icone({ nome, size = 22 }: { nome: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      {ICons[nome]}
    </svg>
  );
}

const NAV = [
  { href: "/inicio", label: "Início", icon: "dashboard" },
  { href: "/transacoes", label: "Extrato", icon: "extrato" },
  { href: "/cartoes", label: "Cartões", icon: "cartoes" },
  { href: "/renda", label: "Renda", icon: "renda" },
  { href: "/relatorios", label: "Relatórios", icon: "relatorios" },
];

function ativo(pathname: string, href: string): boolean {
  return pathname.startsWith(href);
}

function AvatarEmoji({ size = 38 }: { size?: number }) {
  return (
    <span
      className="inline-flex items-center justify-center rounded-full bg-brand-soft"
      style={{ width: size, height: size, fontSize: size * 0.5 }}
    >
      {USUARIO_ATUAL.emoji}
    </span>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-paper">
      {/* Sidebar fixa — desktop */}
      <aside className="fixed left-0 top-0 hidden h-screen w-[280px] flex-col border-r border-line bg-paper px-6 py-7 lg:flex">
        <div className="flex items-start justify-between px-2">
          <div>
            <p className="font-display text-2xl font-bold text-brand">carteirAI</p>
            <p className="text-sm text-muted">Gestão Familiar</p>
          </div>
          <Link href="/notificacoes" className="relative mt-1 text-muted hover:text-ink" aria-label="Notificações">
            <Icone nome="sino" size={22} />
            <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-saida" />
          </Link>
        </div>

        <Link
          href="/transacoes/nova"
          className="mt-7 rounded-md bg-brand-dark py-3 text-center font-body font-semibold text-brand-fg transition-colors hover:bg-brand"
        >
          Adicionar entrada
        </Link>

        <nav className="mt-6 flex flex-1 flex-col gap-1">
          {NAV.map((item) => {
            const on = ativo(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 rounded-md px-3 py-2.5 font-body text-[15px] transition-colors ${
                  on ? "bg-brand text-brand-fg" : "text-ink hover:bg-surface-2"
                }`}
              >
                <Icone nome={item.icon} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Perfil → Conta/Configurações (contém Dispositivos e Sair) */}
        <Link
          href="/conta"
          className="flex items-center gap-3 rounded-md px-2 py-2 transition-colors hover:bg-surface-2"
        >
          <AvatarEmoji size={36} />
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-ink">{USUARIO_ATUAL.nome}</p>
            <p className="text-xs text-muted">Conta e ajustes</p>
          </div>
        </Link>
      </aside>

      {/* Cabeçalho mobile fixo: sino + avatar (avatar → Conta) */}
      <div className="fixed right-4 top-4 z-20 flex items-center gap-3 lg:hidden">
        <Link href="/notificacoes" className="relative flex h-10 w-10 items-center justify-center rounded-full border border-line bg-surface text-ink" aria-label="Notificações">
          <Icone nome="sino" size={20} />
          <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-saida" />
        </Link>
        <Link href="/conta" aria-label="Conta">
          <AvatarEmoji size={40} />
        </Link>
      </div>

      {/* Conteúdo */}
      <main className="min-h-screen px-4 pb-28 pt-5 lg:ml-[280px] lg:px-12 lg:pb-12 lg:pt-9">
        {children}
      </main>

      {/* FAB (+) — mobile: Adicionar entrada */}
      <Link
        href="/transacoes/nova"
        className="fixed bottom-20 right-5 z-20 flex h-14 w-14 items-center justify-center rounded-full bg-brand-dark text-brand-fg shadow-float lg:hidden"
        aria-label="Adicionar entrada"
      >
        <Icone nome="mais" size={26} />
      </Link>

      {/* Tab bar fixa — mobile (5 destinos) */}
      <nav className="fixed bottom-0 left-0 right-0 z-10 flex border-t border-line bg-surface lg:hidden">
        {NAV.map((tab) => {
          const on = ativo(pathname, tab.href);
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={`flex flex-1 flex-col items-center gap-1 py-2.5 text-[10px] font-semibold ${
                on ? "text-brand" : "text-muted"
              }`}
            >
              <Icone nome={tab.icon} size={24} />
              {tab.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
