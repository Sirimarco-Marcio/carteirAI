import { auth } from "@/auth";
import { NextResponse } from "next/server";

export default auth((req) => {
  const { pathname } = req.nextUrl;
  const isAuthed = !!req.auth;

  // Rotas protegidas — redireciona para /login se não autenticado
  if (!isAuthed && pathname.startsWith("/inicio")) {
    return NextResponse.redirect(new URL("/login", req.nextUrl));
  }

  // Já autenticado tentando acessar /login → vai pro painel
  if (isAuthed && pathname === "/login") {
    return NextResponse.redirect(new URL("/inicio", req.nextUrl));
  }
});

export const config = {
  matcher: ["/login", "/inicio/:path*"],
};
