// import UploadForm from "@/components/UploadForm";

// export default function UploadPage() {
//   return (
//     <main className="page">
//       <h1>Upload data</h1>
//       <p className="subtitle">Upload the orders and payments exports, then reconciliation runs automatically.</p>
//       <UploadForm />
//     </main>
//   );
// }


"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";
import UploadForm from "@/components/UploadForm";

export default function UploadPage() {
  const router = useRouter();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    setChecked(true);
  }, [router]);

  if (!checked) return null;

  return (
    <main className="page">
      <h1>Upload data</h1>
      <p className="subtitle">Upload the orders and payments exports, then reconciliation runs automatically.</p>
      <UploadForm />
    </main>
  );
}