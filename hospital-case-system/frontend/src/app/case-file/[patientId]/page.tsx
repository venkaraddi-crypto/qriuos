"use client";
import { useParams } from "next/navigation";
import Shell from "@/components/Shell";
import CaseFile from "@/components/CaseFile";

export default function StaffCaseFile() {
  const { patientId } = useParams<{ patientId: string }>();
  return (
    <Shell portal="staff" title="Case file">
      <CaseFile patientId={Number(patientId)} />
    </Shell>
  );
}
