import "next-auth";
import "next-auth/jwt";

declare module "next-auth" {
  interface User {
    role?: string;
    plan?: string;
    onboardingCompleted?: boolean;
  }
  interface Session {
    user: {
      id: string;
      name?: string | null;
      email?: string | null;
      image?: string | null;
      role: string;
      plan: string;
      onboardingCompleted?: boolean;
    };
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    id: string;
    role: string;
    plan: string;
    onboardingCompleted?: boolean;
    claimsRefreshedAt?: number;
    deletedAt?: string | null;
  }
}
