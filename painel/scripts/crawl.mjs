/**
 * Crawler de ligações do painel — abre o app no Chrome, descobre todos os links/botões
 * internos a partir das telas semente, navega em cada um e cataloga os "becos sem saída"
 * (404, href vazio/"#", links que não levam a lugar nenhum).
 *
 * Uso: BASE_URL=http://localhost:3030 node scripts/crawl.mjs
 * Requer: playwright-core + Chrome do sistema (/usr/bin/google-chrome).
 */
import { chromium } from "playwright-core";

const BASE = process.env.BASE_URL || "http://localhost:3030";
const CHROME = process.env.CHROME_PATH || "/usr/bin/google-chrome";
const SEEDS = ["/", "/login"];

const visitados = new Map(); // rota -> status
const linksMortos = []; // {origem, texto, alvo, motivo}
const botoesSemAlvo = []; // {origem, texto}

function interno(href) {
  if (!href) return null;
  if (href.startsWith("#") || href.startsWith("javascript:") || href.startsWith("mailto:")) return null;
  try {
    const u = new URL(href, BASE);
    if (u.origin !== new URL(BASE).origin) return null;
    return u.pathname;
  } catch {
    return null;
  }
}

const browser = await chromium.launch({ executablePath: CHROME, args: ["--no-sandbox"] });
const page = await browser.newPage();

const fila = [...SEEDS];
while (fila.length) {
  const rota = fila.shift();
  if (visitados.has(rota)) continue;

  const resp = await page
    .goto(BASE + rota, { waitUntil: "domcontentloaded", timeout: 20000 })
    .catch((e) => {
      console.error(`   ! goto falhou em ${rota}: ${e.message.split("\n")[0]}`);
      return null;
    });
  const status = resp ? resp.status() : 0;
  visitados.set(rota, status);

  if (status === 404 || status === 0) continue; // não explora página quebrada

  // Coleta âncoras (links)
  const ancoras = await page.$$eval("a", (els) =>
    els.map((a) => ({ href: a.getAttribute("href"), texto: (a.textContent || "").trim().slice(0, 40) })),
  );
  for (const a of ancoras) {
    const alvo = interno(a.href);
    if (alvo === null) {
      if (a.href === "#" || a.href === "" || a.href == null) {
        linksMortos.push({ origem: rota, texto: a.texto, alvo: a.href ?? "(vazio)", motivo: "link sem destino" });
      }
      continue;
    }
    if (!visitados.has(alvo) && !fila.includes(alvo)) fila.push(alvo);
  }

  // Coleta botões (não navegam por href; listamos pra revisão de handler)
  const botoes = await page.$$eval("button", (els) =>
    els.map((b) => (b.textContent || b.getAttribute("aria-label") || "").trim().slice(0, 40)).filter(Boolean),
  );
  for (const texto of botoes) botoesSemAlvo.push({ origem: rota, texto });
}

await browser.close();

// Relatório
const rotas404 = [...visitados.entries()].filter(([, s]) => s === 404).map(([r]) => r);
const rotasOk = [...visitados.entries()].filter(([, s]) => s === 200).map(([r]) => r);

console.log("\n===== RELATÓRIO DE LIGAÇÕES =====\n");
console.log("✅ Rotas OK (200):", rotasOk.join(", ") || "(nenhuma)");
console.log("\n❌ Rotas 404 (página não existe / link quebrado):");
for (const r of rotas404) console.log("   -", r);
console.log("\n⚠️  Links sem destino (href '#'/vazio):");
for (const l of linksMortos) console.log(`   - [${l.origem}] "${l.texto}" → ${l.alvo}`);
console.log("\n🔘 Botões encontrados (verificar se têm ação):");
const porPagina = {};
for (const b of botoesSemAlvo) (porPagina[b.origem] ??= []).push(b.texto);
for (const [pag, lista] of Object.entries(porPagina)) console.log(`   [${pag}] ${lista.join(" | ")}`);

console.log("\n===== RESUMO =====");
console.log(`Rotas visitadas: ${visitados.size} | OK: ${rotasOk.length} | 404: ${rotas404.length} | links mortos: ${linksMortos.length}`);
process.exit(0);
