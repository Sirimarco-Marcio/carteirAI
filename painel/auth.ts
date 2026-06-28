import NextAuth, { type DefaultSession } from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { neon } from "@neondatabase/serverless";
import bcrypt from "bcryptjs";

// ---------------------------------------------------------------------------
// Extensão de tipos — adiciona id e familiaId à sessão
// ---------------------------------------------------------------------------
declare module "next-auth" {
  interface Session {
    user: {
      id: string;
      familiaId: string;
    } & DefaultSession["user"];
  }
}

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Credentials({
      credentials: {
        email: { label: "E-mail", type: "email" },
        password: { label: "Senha", type: "password" },
      },
      async authorize(credentials) {
        const email = (credentials?.email as string | undefined)?.trim().toLowerCase();
        const password = credentials?.password as string | undefined;
        if (!email || !password) return null;

        const sql = neon(process.env.DATABASE_URL!);
        const rows = await sql`
          SELECT ac.senha_hash, ac.usuario_id, u.nome, u.familia_id
          FROM   auth_credentials ac
          JOIN   usuarios u ON u.id = ac.usuario_id
          WHERE  ac.email = ${email}
          LIMIT  1
        `;
        const row = rows[0];
        if (!row) return null;

        const ok = await bcrypt.compare(password, row.senha_hash as string);
        if (!ok) return null;

        return {
          id:       row.usuario_id as string,
          name:     row.nome      as string,
          email,
          familiaId: row.familia_id as string,
        };
      },
    }),
  ],

  callbacks: {
    jwt({ token, user }) {
      if (user) {
        token.familiaId = (user as { familiaId: string }).familiaId;
      }
      return token;
    },
    session({ session, token }) {
      session.user.id       = token.sub!;
      session.user.familiaId = token.familiaId as string;
      return session;
    },
  },

  pages: {
    signIn: "/login",
  },
});
