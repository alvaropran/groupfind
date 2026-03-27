import { z } from "zod";

const MAX_FILE_SIZE = 500 * 1024 * 1024; // 500MB

export const zipFileSchema = z.object({
  name: z.string().refine((name) => name.endsWith(".zip"), {
    message: "File must be a .zip file",
  }),
  size: z.number().max(MAX_FILE_SIZE, {
    message: "File must be under 500MB",
  }),
  type: z.string().refine(
    (type) =>
      type === "application/zip" ||
      type === "application/x-zip-compressed" ||
      type === "application/octet-stream",
    { message: "File must be a ZIP archive" },
  ),
});

export type ZipFileValidation = z.infer<typeof zipFileSchema>;

export function validateZipFile(file: File): {
  readonly valid: boolean;
  readonly error: string | null;
} {
  const result = zipFileSchema.safeParse({
    name: file.name,
    size: file.size,
    type: file.type,
  });

  if (result.success) {
    return { valid: true, error: null };
  }

  const firstIssue = result.error.issues[0];
  return { valid: false, error: firstIssue?.message ?? "Invalid file" };
}
