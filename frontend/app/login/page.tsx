import { LoginForm } from "../../components/LoginForm";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  const params = await searchParams;

  return (
    <main className="shell loginShell">
      <LoginForm nextPath={params.next ?? "/"} />
    </main>
  );
}
