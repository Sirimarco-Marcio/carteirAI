"use client";

import Link from "next/link";
import { useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [verSenha, setVerSenha]   = useState(false);
  const [email, setEmail]         = useState("");
  const [senha, setSenha]         = useState("");
  const [erro, setErro]           = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);
    setCarregando(true);

    const result = await signIn("credentials", {
      email: email.trim().toLowerCase(),
      password: senha,
      redirect: false,
    });

    setCarregando(false);

    if (!result || result.error) {
      setErro("E-mail ou senha incorretos.");
    } else {
      router.push("/inicio");
      router.refresh();
    }
  }

  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      {/* Painel da marca */}
      <div className="relative flex flex-col justify-center overflow-hidden bg-brand px-8 py-12 lg:w-1/2 lg:px-16">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.15]"
          style={{
            backgroundImage: "radial-gradient(#ffffff 1px, transparent 1px)",
            backgroundSize: "20px 20px",
          }}
        />
        <div className="pointer-events-none absolute -bottom-24 left-1/2 h-72 w-[140%] -translate-x-1/2 rounded-[50%] bg-brand-dark/40 blur-2xl" />
        <div className="relative">
          <p className="font-display text-4xl font-bold text-[#a5f2d9] lg:text-5xl">carteirAI</p>
          <p className="mt-3 max-w-sm text-lg text-[#d6e6e0]">As contas da família, no mesmo lugar.</p>
        </div>
      </div>

      {/* Formulário */}
      <div className="flex flex-1 items-center justify-center bg-paper px-6 py-12">
        <div className="w-full max-w-sm rounded-lg border border-line bg-surface p-7 shadow-float">
          <h1 className="font-display text-2xl font-semibold text-ink">Entrar</h1>

          <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
            <div>
              <input
                type="email"
                placeholder="E-mail"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full rounded-md border border-line bg-surface px-4 py-3 text-ink outline-none transition focus:border-brand focus:ring-[3px] focus:ring-brand-soft"
              />
            </div>
            <div className="relative">
              <input
                type={verSenha ? "text" : "password"}
                placeholder="Senha"
                autoComplete="current-password"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                required
                className="w-full rounded-md border border-line bg-surface px-4 py-3 pr-11 text-ink outline-none transition focus:border-brand focus:ring-[3px] focus:ring-brand-soft"
              />
              <button
                type="button"
                onClick={() => setVerSenha((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-ink"
                aria-label={verSenha ? "Ocultar senha" : "Mostrar senha"}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
                  <circle cx="12" cy="12" r="3" />
                  {!verSenha && <path d="M4 4l16 16" strokeLinecap="round" />}
                </svg>
              </button>
            </div>

            {erro && (
              <div className="flex items-center gap-2 rounded-md border border-saida/30 bg-saida/5 px-4 py-2.5 text-sm text-saida">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="flex-shrink-0">
                  <circle cx="12" cy="12" r="9" /><path d="M12 8v5M12 16.5v.5" strokeLinecap="round" />
                </svg>
                {erro}
              </div>
            )}

            <button
              type="submit"
              disabled={carregando}
              className="flex w-full items-center justify-center gap-2 rounded-md bg-brand-dark py-3 font-semibold text-brand-fg transition-colors hover:bg-brand disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {carregando ? (
                <>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="animate-spin">
                    <circle cx="12" cy="12" r="9" strokeOpacity="0.25" />
                    <path d="M12 3a9 9 0 0 1 9 9" strokeLinecap="round" />
                  </svg>
                  Entrando…
                </>
              ) : "Entrar"}
            </button>
          </form>

          <Link
            href="/onboarding"
            className="mt-3 block rounded-md bg-surface-2 py-3 text-center font-medium text-ink transition-colors hover:bg-line"
          >
            Criar conta da família
          </Link>

          <Link href="#" className="mt-4 block text-center text-sm font-medium text-brand">
            Esqueci minha senha
          </Link>
        </div>
      </div>
    </div>
  );
}
